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
    """質問一覧を取得"""
    query = db.query(Question)
    
    if lecture_id:
        query = query.filter(Question.lecture_id == lecture_id)
    
    if difficulty:
        try:
            query = query.filter(Question.difficulty == DifficultyLevel(difficulty))
        except ValueError:
            raise HTTPException(status_code=400, detail="無効な難易度です")
    
    if question_type:
        try:
            query = query.filter(Question.question_type == QuestionType(question_type))
        except ValueError:
            raise HTTPException(status_code=400, detail="無効な質問タイプです")
    
    questions = query.offset(skip).limit(limit).all()
    return [question.to_dict() for question in questions]


@router.get("/{question_id}", response_model=dict)
async def get_question(question_id: int, db: Session = Depends(get_db)):
    """特定の質問を取得"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="質問が見つかりません")
    
    question_dict = question.to_dict()
    
    # 講義情報も含める
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
    """質問を更新"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="質問が見つかりません")
    
    try:
        question.question_text = question_text
        question.correct_answer = correct_answer
        if explanation:
            question.explanation = explanation
        
        db.commit()
        db.refresh(question)
        
        logger.info(f"質問が更新されました: {question_id}")
        
        return {"message": "質問が更新されました", "question": question.to_dict()}
        
    except Exception as e:
        logger.error(f"質問更新エラー: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"質問の更新に失敗しました: {str(e)}")


@router.delete("/{question_id}")
async def delete_question(question_id: int, db: Session = Depends(get_db)):
    """質問を削除"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="質問が見つかりません")
    
    try:
        db.delete(question)
        db.commit()
        
        logger.info(f"質問が削除されました: {question_id}")
        
        return {"message": "質問が削除されました"}
        
    except Exception as e:
        logger.error(f"質問削除エラー: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"質問の削除に失敗しました: {str(e)}")


@router.post("/{question_id}/answer")
async def submit_answer(
    question_id: int,
    student_id: str = Form(...),
    response_text: str = Form(...),
    response_time: Optional[int] = Form(None),
    confidence_level: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """学生の回答を提出"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="質問が見つかりません")
    
    try:
        # 正解かどうかを判定
        is_correct = _evaluate_answer(question, response_text)
        
        # 得点を計算
        score = 100.0 if is_correct else 0.0
        
        # 学生の回答を記録
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
        
        # 質問の使用回数を更新
        question.usage_count += 1
        
        # 正答率を更新
        _update_correct_rate(question, db)
        
        db.commit()
        db.refresh(student_response)
        
        logger.info(f"学生回答が記録されました: 質問 {question_id}, 学生 {student_id}")
        
        return {
            "message": "回答が記録されました",
            "is_correct": is_correct,
            "score": score,
            "explanation": question.explanation
        }
        
    except Exception as e:
        logger.error(f"回答記録エラー: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"回答の記録に失敗しました: {str(e)}")


def _evaluate_answer(question: Question, response_text: str) -> bool:
    """回答を評価"""
    if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.SINGLE_CHOICE]:
        # 選択式の場合、正解と完全一致で判定
        return response_text.strip().lower() == question.correct_answer.strip().lower()
    
    elif question.question_type == QuestionType.SHORT_ANSWER:
        # 短答式の場合、部分一致で判定
        correct_answer = question.correct_answer.strip().lower()
        student_answer = response_text.strip().lower()
        
        # キーワードベースの評価
        if question.keywords:
            keywords = [kw.lower() for kw in question.get_keywords_list()]
            matches = sum(1 for kw in keywords if kw in student_answer)
            return matches >= len(keywords) * 0.5  # 半分以上のキーワードが含まれている
        
        # 正解との類似度評価（簡単な実装）
        return correct_answer in student_answer or student_answer in correct_answer
    
    else:  # ESSAY
        # 記述式の場合、簡単なキーワードマッチング
        if question.keywords:
            keywords = [kw.lower() for kw in question.get_keywords_list()]
            student_answer = response_text.strip().lower()
            matches = sum(1 for kw in keywords if kw in student_answer)
            return matches >= max(1, len(keywords) * 0.3)  # 最低30%のキーワードが含まれている
        
        # キーワードがない場合は中立的な評価
        return len(response_text.strip()) >= 50  # 最低50文字以上の回答


def _update_correct_rate(question: Question, db: Session):
    """質問の正答率を更新"""
    try:
        # この質問のすべての回答を取得
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
        logger.error(f"正答率更新エラー: {e}")


@router.get("/statistics/overview")
async def get_statistics_overview(db: Session = Depends(get_db)):
    """質問統計の概要を取得"""
    try:
        # 総質問数
        total_questions = db.query(Question).count()
        
        # 難易度別の質問数
        difficulty_stats = db.query(
            Question.difficulty,
            func.count(Question.id)
        ).group_by(Question.difficulty).all()
        
        # 質問タイプ別の質問数
        type_stats = db.query(
            Question.question_type,
            func.count(Question.id)
        ).group_by(Question.question_type).all()
        
        # 総回答数
        total_responses = db.query(StudentResponse).count()
        
        # 平均正答率
        avg_correct_rate = db.query(func.avg(Question.correct_rate)).scalar()
        
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
        logger.error(f"統計取得エラー: {e}")
        raise HTTPException(status_code=500, detail="統計の取得に失敗しました")


@router.get("/{question_id}/responses", response_model=List[dict])
async def get_question_responses(
    question_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """特定の質問への回答一覧を取得"""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="質問が見つかりません")
    
    responses = db.query(StudentResponse).filter(
        StudentResponse.question_id == question_id
    ).offset(skip).limit(limit).all()
    
    return [response.to_dict() for response in responses]