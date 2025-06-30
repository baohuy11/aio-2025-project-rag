"""
Lectures API router
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import json
from pathlib import Path
import shutil

from src.qa_system.models.base import get_db
from src.qa_system.models.lecture import Lecture
from src.qa_system.services.pptx_extractor import PPTXExtractor
from src.qa_system.services.qa_generator import QAGenerator
from src.qa_system.models.question import Question, QuestionType, DifficultyLevel
from src.qa_system.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_lectures(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get list of lectures"""
    lectures = db.query(Lecture).offset(skip).limit(limit).all()
    return [lecture.to_dict() for lecture in lectures]


@router.get("/{lecture_id}", response_model=dict)
async def get_lecture(lecture_id: int, db: Session = Depends(get_db)):
    """Get a specific lecture"""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return lecture.to_dict()


@router.post("/upload", response_model=dict)
async def upload_lecture(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a PowerPoint file and create a lecture"""
    
    # Check file extension
    if not file.filename.lower().endswith(('.pptx', '.ppt')):
        raise HTTPException(
            status_code=400, 
            detail="Only PowerPoint files (.pptx or .ppt) can be uploaded"
        )
    
    # Check file size
    if file.size > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds the limit ({settings.max_file_size // 1024 // 1024}MB)"
        )
    
    try:
        # Save file
        upload_dir = Path(settings.upload_folder)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create lecture record
        lecture = Lecture(
            title=title,
            description=description,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file.size,
            author=author,
            subject=subject,
            processing_status="uploaded"
        )
        
        db.add(lecture)
        db.commit()
        db.refresh(lecture)
        
        # Run content extraction and QA generation in background
        background_tasks.add_task(
            process_lecture_content,
            lecture.id,
            str(file_path)
        )
        
        logger.info(f"Lecture uploaded: {lecture.id}")
        
        return {
            "message": "Lecture uploaded. Content extraction and QA generation will start.",
            "lecture_id": lecture.id
        }
        
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


async def process_lecture_content(lecture_id: int, file_path: str):
    """Process lecture content (background task)"""
    from src.qa_system.models.base import SessionLocal
    
    db = SessionLocal()
    try:
        lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
        if not lecture:
            logger.error(f"Lecture not found: {lecture_id}")
            return
        
        # Start processing
        lecture.processing_status = "processing"
        db.commit()
        
        # Extract PowerPoint content
        extractor = PPTXExtractor()
        slides_content = extractor.extract_from_file(Path(file_path))
        
        # Save extracted content
        lecture.total_slides = len(slides_content)
        lecture.extracted_content = json.dumps(
            [slide.to_dict() for slide in slides_content], 
            ensure_ascii=False
        )
        
        # QA generation
        if settings.google_api_key:
            qa_generator = QAGenerator(settings.google_api_key, settings.gemini_model)
            
            # Generate QA for each slide (limit max number for performance)
            slides_data = [slide.to_dict() for slide in slides_content[:settings.max_slides_for_qa]]
            qa_sets = qa_generator.generate_questions_for_multiple_slides(
                slides_data, 
                questions_per_slide=settings.qa_per_slide
            )
            
            logger.info(f"QA generation target: {len(slides_data)} slides (out of {len(slides_content)})")
            
            # Save questions to database
            for qa_set in qa_sets:
                for question_data in qa_set.questions:
                    question = Question(
                        lecture_id=lecture.id,
                        slide_number=qa_set.slide_number,
                        question_text=question_data.question,
                        question_type=QuestionType(question_data.question_type),
                        difficulty=DifficultyLevel(question_data.difficulty),
                        correct_answer=question_data.correct_answer,
                        explanation=question_data.explanation,
                        choices=question_data.choices,
                        keywords=question_data.keywords
                    )
                    db.add(question)
            
            logger.info(f"QA generation completed for lecture {lecture_id}: {len([q for qa_set in qa_sets for q in qa_set.questions])} questions")
        
        # Processing complete
        lecture.is_processed = True
        lecture.processing_status = "completed"
        db.commit()
        
        logger.info(f"Processing completed for lecture {lecture_id}")
        
    except Exception as e:
        logger.error(f"Lecture processing error: {e}")
        
        # Update error status
        if lecture:
            lecture.processing_status = "error"
            lecture.error_message = str(e)
            db.commit()
    
    finally:
        db.close()


@router.delete("/{lecture_id}")
async def delete_lecture(lecture_id: int, db: Session = Depends(get_db)):
    """Delete a lecture"""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    try:
        # Delete file
        file_path = Path(lecture.file_path)
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database (related questions are also deleted automatically)
        db.delete(lecture)
        db.commit()
        
        logger.info(f"Lecture deleted: {lecture_id}")
        
        return {"message": "Lecture deleted"}
        
    except Exception as e:
        logger.error(f"Lecture deletion error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete lecture: {str(e)}")


@router.get("/{lecture_id}/questions", response_model=List[dict])
async def get_lecture_questions(
    lecture_id: int,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of questions for a specific lecture"""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    query = db.query(Question).filter(Question.lecture_id == lecture_id)
    
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    
    if question_type:
        query = query.filter(Question.question_type == question_type)
    
    questions = query.all()
    return [question.to_dict() for question in questions]


@router.get("/{lecture_id}/slides")
async def get_lecture_slides(lecture_id: int, db: Session = Depends(get_db)):
    """Get slide content for a lecture"""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    if not lecture.extracted_content:
        return {"slides": []}
    
    try:
        slides = json.loads(lecture.extracted_content)
        return {"slides": slides}
    except Exception as e:
        logger.error(f"Failed to load slides: {e}")
        raise HTTPException(status_code=500, detail="Failed to load slides")