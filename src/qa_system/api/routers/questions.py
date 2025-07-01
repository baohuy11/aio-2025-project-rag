"""
Questions API router
"""

from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import logging

from src.qa_system.models.base import get_db
from src.qa_system.models.question import Question, QuestionType, DifficultyLevel
from src.qa_system.models.student_response import StudentResponse
from src.qa_system.models.lecture import Lecture

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_questions(
    skip: int = 0,
    limit: int = 100,
    lecture_id: Optional[int] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get question list"""
    query = db.query(Question)
    
    if lecture_id:
        query = query.filter(Question.lecture_id == lecture_id)
    
    if difficulty:
        try:
            query = query.filter(Question.difficulty == DifficultyLevel(difficulty))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid difficulty level")
    
    if question_type:
        try:
            query = query.filter(Question.question_type == QuestionType(question_type))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid question type")
    
    questions = query.offset(skip).limit(limit).all()
    return [question.to_dict() for question in questions]


@router.get("/{question_id}", response_model=dict)
async def get_question(question_id: int, db: Session = Depends(get_db)):
    """Get a specific question"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question_dict = question.to_dict()
    
    # Include lecture information
    lecture = db.query(Lecture).filter(Lecture.id == question.lecture_id).first()
    if lecture:
        question_dict["lecture"] = {"id": lecture.id, "title": lecture.title}
    
    return question_dict


@router.put("/{question_id}")
async def update_question(
    question_id: int,
    question_text: str = Form(...),
    correct_answer: str = Form(...),
    explanation: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Update question"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    try:
        question.question_text = question_text
        question.correct_answer = correct_answer
        if explanation:
            question.explanation = explanation
        
        db.commit()
        db.refresh(question)
        
        logger.info(f"Question updated: {question_id}")
        
        return {"message": "Question updated", "question": question.to_dict()}
        
    except Exception as e:
        logger.error(f"Question update error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update question: {str(e)}")


@router.delete("/{question_id}")
async def delete_question(question_id: int, db: Session = Depends(get_db)):
    """Delete question"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    try:
        db.delete(question)
        db.commit()
        
        logger.info(f"Question deleted: {question_id}")
        
        return {"message": "Question deleted"}
        
    except Exception as e:
        logger.error(f"Question deletion error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete question: {str(e)}")


@router.post("/{question_id}/answer")
async def submit_answer(
    question_id: int,
    student_id: str = Form(...),
    response_text: str = Form(...),
    response_time: Optional[int] = Form(None),
    confidence_level: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """Submit student answer"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    try:
        # Evaluate if answer is correct
        is_correct = _evaluate_answer(question, response_text)
        
        # Calculate score
        score = 100.0 if is_correct else 0.0
        
        # Record student response
        student_response = StudentResponse(
            question_id=question_id,
            student_id=student_id,
            response_text=response_text,
            is_correct=is_correct,
            score=score,
            response_time=response_time,
            confidence_level=confidence_level
        )
        
        db.add(student_response)
        
        # Update question usage count
        question.usage_count += 1
        
        # Update correct answer rate
        _update_correct_rate(question, db)
        
        db.commit()
        db.refresh(student_response)
        
        logger.info(f"Student response recorded: Question {question_id}, Student {student_id}")
        
        return {
            "message": "Answer recorded",
            "is_correct": is_correct,
            "score": score,
            "explanation": question.explanation
        }
        
    except Exception as e:
        logger.error(f"Answer recording error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record answer: {str(e)}")


def _evaluate_answer(question: Question, response_text: str) -> bool:
    """Evaluate answer"""
    if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.SINGLE_CHOICE]:
        # For multiple choice, check exact match
        return response_text.strip().lower() == question.correct_answer.strip().lower()
    
    elif question.question_type == QuestionType.SHORT_ANSWER:
        # For short answer, check partial match
        correct_answer = question.correct_answer.strip().lower()
        student_answer = response_text.strip().lower()
        
        # Keyword-based evaluation
        if question.keywords:
            keywords = [kw.lower() for kw in question.get_keywords_list()]
            matches = sum(1 for kw in keywords if kw in student_answer)
            return matches >= len(keywords) * 0.5  # At least half of keywords included
        
        # Similarity evaluation with correct answer (simple implementation)
        return correct_answer in student_answer or student_answer in correct_answer
    
    else:  # ESSAY
        # For essay, simple keyword matching
        if question.keywords:
            keywords = [kw.lower() for kw in question.get_keywords_list()]
            student_answer = response_text.strip().lower()
            matches = sum(1 for kw in keywords if kw in student_answer)
            return matches >= max(1, len(keywords) * 0.3)  # At least 30% of keywords included
        
        # If no keywords, neutral evaluation
        return len(response_text.strip()) >= 50  # At least 50 characters


def _update_correct_rate(question: Question, db: Session):
    """Update question correct answer rate"""
    try:
        # Get all responses for this question
        responses = db.query(StudentResponse).filter(
            StudentResponse.question_id == question.id,
            StudentResponse.is_correct.isnot(None)
        ).all()
        
        if responses:
            correct_count = sum(1 for r in responses if r.is_correct)
            total_count = len(responses)
            correct_rate = int((correct_count / total_count) * 100)
            
            question.correct_rate = correct_rate
            
    except Exception as e:
        logger.error(f"Correct rate update error: {e}")


@router.get("/statistics/overview")
async def get_statistics_overview(db: Session = Depends(get_db)):
    """Get question statistics overview"""
    try:
        # Total questions
        total_questions = db.query(Question).count()
        
        # Questions by difficulty
        difficulty_stats = db.query(
            Question.difficulty,
            func.count(Question.id)
        ).group_by(Question.difficulty).all()
        
        # Questions by type
        type_stats = db.query(
            Question.question_type,
            func.count(Question.id)
        ).group_by(Question.question_type).all()
        
        # Average correct rate
        avg_correct_rate = db.query(func.avg(Question.correct_rate)).scalar()

        # avg_correct_rate = db.query(func.avg(Question.correct_rate)).filter(
            # Question.correct_rate.isnot(None)
        # ).scalar()
        
        # Total responses
        total_responses = db.query(StudentResponse).count()
        
        return {
            "total_questions": total_questions,
            "total_responses": total_responses,
            "average_correct_rate": round(avg_correct_rate, 1) if avg_correct_rate else 0,
            "difficulty_distribution": {
                difficulty.value: count for difficulty, count in difficulty_stats
            },
            "type_distribution": {
                q_type.value: count for q_type, count in type_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Statistics overview error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics overview")


@router.get("/{question_id}/responses", response_model=List[dict])
async def get_question_responses(
    question_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get responses for a specific question"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    responses = db.query(StudentResponse).filter(
        StudentResponse.question_id == question_id
    ).offset(skip).limit(limit).all()
    
    return [response.to_dict() for response in responses]