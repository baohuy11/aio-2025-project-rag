"""
Analytics API router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from src.qa_system.models.base import get_db
from src.qa_system.models.question import Question, QuestionType, DifficultyLevel
from src.qa_system.models.student_response import StudentResponse
from src.qa_system.models.lecture import Lecture

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_data(db: Session = Depends(get_db)):
    """Get data for dashboard"""
    try:
        # Basic statistics
        total_lectures = db.query(Lecture).count()
        total_questions = db.query(Question).count()
        total_responses = db.query(StudentResponse).count()
        
        # Average correct rate
        avg_correct_rate = db.query(func.avg(Question.correct_rate)).filter(
            Question.correct_rate.isnot(None)
        ).scalar()
        
        # Recent activity (past 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_responses = db.query(StudentResponse).filter(
            StudentResponse.submitted_at >= week_ago
        ).count()
        
        # Statistics by difficulty
        difficulty_stats = db.query(
            Question.difficulty,
            func.count(Question.id).label('question_count'),
            func.avg(Question.correct_rate).label('avg_correct_rate')
        ).filter(
            Question.correct_rate.isnot(None)
        ).group_by(Question.difficulty).all()
        
        difficulty_data = {}
        for diff, q_count, avg_rate in difficulty_stats:
            difficulty_data[diff.value] = {
                "question_count": q_count,
                "average_correct_rate": round(avg_rate, 1) if avg_rate else 0
            }
        
        # Statistics by question type
        type_stats = db.query(
            Question.question_type,
            func.count(Question.id).label('question_count'),
            func.avg(Question.correct_rate).label('avg_correct_rate')
        ).filter(
            Question.correct_rate.isnot(None)
        ).group_by(Question.question_type).all()
        
        type_data = {}
        for q_type, q_count, avg_rate in type_stats:
            type_data[q_type.value] = {
                "question_count": q_count,
                "average_correct_rate": round(avg_rate, 1) if avg_rate else 0
            }
        
        return {
            "overview": {
                "total_lectures": total_lectures,
                "total_questions": total_questions,
                "total_responses": total_responses,
                "average_correct_rate": round(avg_correct_rate, 1) if avg_correct_rate else 0,
                "recent_responses": recent_responses
            },
            "difficulty_analysis": difficulty_data,
            "type_analysis": type_data
        }
        
    except Exception as e:
        logger.error(f"Dashboard data retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


@router.get("/lecture/{lecture_id}/performance")
async def get_lecture_performance(lecture_id: int, db: Session = Depends(get_db)):
    """Performance analysis for a specific lecture"""
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    try:
        # Get lecture questions
        questions = db.query(Question).filter(Question.lecture_id == lecture_id).all()
        
        if not questions:
            return {
                "lecture_id": lecture_id,
                "lecture_title": lecture.title,
                "message": "No questions available for this lecture yet"
            }
        
        # Statistics for each question
        question_stats = []
        for question in questions:
            responses = db.query(StudentResponse).filter(
                StudentResponse.question_id == question.id
            ).all()
            
            if responses:
                correct_count = sum(1 for r in responses if r.is_correct)
                total_count = len(responses)
                correct_rate = (correct_count / total_count) * 100
                
                avg_response_time = sum(
                    r.response_time for r in responses if r.response_time
                ) / len([r for r in responses if r.response_time]) if any(r.response_time for r in responses) else None
                
                question_stats.append({
                    "question_id": question.id,
                    "slide_number": question.slide_number,
                    "question_text": question.question_text[:100] + "..." if len(question.question_text) > 100 else question.question_text,
                    "difficulty": question.difficulty.value,
                    "question_type": question.question_type.value,
                    "response_count": total_count,
                    "correct_rate": round(correct_rate, 1),
                    "average_response_time": round(avg_response_time, 1) if avg_response_time else None
                })
        
        # Overall lecture statistics
        all_responses = db.query(StudentResponse).join(Question).filter(
            Question.lecture_id == lecture_id
        ).all()
        
        overall_stats = {
            "total_questions": len(questions),
            "total_responses": len(all_responses),
            "overall_correct_rate": 0,
            "difficulty_breakdown": {},
            "type_breakdown": {}
        }
        
        if all_responses:
            correct_responses = sum(1 for r in all_responses if r.is_correct)
            overall_stats["overall_correct_rate"] = round(
                (correct_responses / len(all_responses)) * 100, 1
            )
        
        # Breakdown by difficulty
        for difficulty in DifficultyLevel:
            diff_questions = [q for q in questions if q.difficulty == difficulty]
            if diff_questions:
                diff_responses = db.query(StudentResponse).join(Question).filter(
                    and_(Question.lecture_id == lecture_id, Question.difficulty == difficulty)
                ).all()
                
                if diff_responses:
                    correct_count = sum(1 for r in diff_responses if r.is_correct)
                    overall_stats["difficulty_breakdown"][difficulty.value] = {
                        "question_count": len(diff_questions),
                        "response_count": len(diff_responses),
                        "correct_rate": round((correct_count / len(diff_responses)) * 100, 1)
                    }
        
        # Breakdown by question type
        for q_type in QuestionType:
            type_questions = [q for q in questions if q.question_type == q_type]
            if type_questions:
                type_responses = db.query(StudentResponse).join(Question).filter(
                    and_(Question.lecture_id == lecture_id, Question.question_type == q_type)
                ).all()
                
                if type_responses:
                    correct_count = sum(1 for r in type_responses if r.is_correct)
                    overall_stats["type_breakdown"][q_type.value] = {
                        "question_count": len(type_questions),
                        "response_count": len(type_responses),
                        "correct_rate": round((correct_count / len(type_responses)) * 100, 1)
                    }
        
        return {
            "lecture_id": lecture_id,
            "lecture_title": lecture.title,
            "overall_statistics": overall_stats,
            "question_statistics": question_stats
        }
        
    except Exception as e:
        logger.error(f"Lecture performance analysis error: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze lecture performance")


@router.get("/student/{student_id}/progress")
async def get_student_progress(student_id: str, db: Session = Depends(get_db)):
    """Progress analysis for a specific student"""
    try:
        # Get all student responses
        responses = db.query(StudentResponse).filter(
            StudentResponse.student_id == student_id
        ).order_by(StudentResponse.submitted_at.desc()).all()
        
        if not responses:
            return {
                "student_id": student_id,
                "message": "No response records for this student"
            }
        
        # Basic statistics
        total_responses = len(responses)
        correct_responses = sum(1 for r in responses if r.is_correct)
        overall_correct_rate = (correct_responses / total_responses) * 100
        
        # Performance by difficulty
        difficulty_performance = {}
        for difficulty in DifficultyLevel:
            diff_responses = db.query(StudentResponse).join(Question).filter(
                and_(
                    StudentResponse.student_id == student_id,
                    Question.difficulty == difficulty
                )
            ).all()
            
            if diff_responses:
                correct_count = sum(1 for r in diff_responses if r.is_correct)
                difficulty_performance[difficulty.value] = {
                    "total_attempts": len(diff_responses),
                    "correct_count": correct_count,
                    "correct_rate": round((correct_count / len(diff_responses)) * 100, 1)
                }
        
        # Performance by question type
        type_performance = {}
        for q_type in QuestionType:
            type_responses = db.query(StudentResponse).join(Question).filter(
                and_(
                    StudentResponse.student_id == student_id,
                    Question.question_type == q_type
                )
            ).all()
            
            if type_responses:
                correct_count = sum(1 for r in type_responses if r.is_correct)
                type_performance[q_type.value] = {
                    "total_attempts": len(type_responses),
                    "correct_count": correct_count,
                    "correct_rate": round((correct_count / len(type_responses)) * 100, 1)
                }
        
        # Recent activity (latest 10 questions)
        recent_responses = responses[:10]
        recent_activity = []
        for response in recent_responses:
            question = db.query(Question).filter(Question.id == response.question_id).first()
            if question:
                lecture = db.query(Lecture).filter(Lecture.id == question.lecture_id).first()
                recent_activity.append({
                    "submitted_at": response.submitted_at.isoformat(),
                    "lecture_title": lecture.title if lecture else "Unknown",
                    "question_text": question.question_text[:100] + "..." if len(question.question_text) > 100 else question.question_text,
                    "difficulty": question.difficulty.value,
                    "is_correct": response.is_correct,
                    "response_time": response.response_time
                })
        
        # Learning trends analysis
        learning_trends = _analyze_learning_trends(responses)
        
        return {
            "student_id": student_id,
            "overall_statistics": {
                "total_responses": total_responses,
                "correct_responses": correct_responses,
                "overall_correct_rate": round(overall_correct_rate, 1)
            },
            "difficulty_performance": difficulty_performance,
            "type_performance": type_performance,
            "recent_activity": recent_activity,
            "learning_trends": learning_trends
        }
        
    except Exception as e:
        logger.error(f"Student progress analysis error: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze student progress")


def _analyze_learning_trends(responses: List[StudentResponse]) -> Dict[str, Any]:
    """Analyze learning trends"""
    if len(responses) < 5:
        return {"message": "Insufficient data for trend analysis"}
    
    # Correct rate changes over time (latest 20 questions)
    recent_responses = sorted(responses[:20], key=lambda x: x.submitted_at)
    correct_rates = []
    
    for i in range(0, len(recent_responses), 5):
        batch = recent_responses[i:i+5]
        if len(batch) >= 3:  # Calculate with at least 3 questions
            correct_count = sum(1 for r in batch if r.is_correct)
            rate = (correct_count / len(batch)) * 100
            correct_rates.append(rate)
    
    # Trend determination
    trend = "Stable"
    if len(correct_rates) >= 2:
        if correct_rates[-1] > correct_rates[0] + 10:
            trend = "Improving"
        elif correct_rates[-1] < correct_rates[0] - 10:
            trend = "Declining"
    
    # Average response time analysis
    timed_responses = [r for r in responses if r.response_time]
    avg_response_time = None
    if timed_responses:
        avg_response_time = sum(r.response_time for r in timed_responses) / len(timed_responses)
    
    return {
        "performance_trend": trend,
        "recent_correct_rates": correct_rates,
        "average_response_time": round(avg_response_time, 1) if avg_response_time else None
    }


@router.get("/insights/recommendations")
async def get_learning_recommendations(
    lecture_id: Optional[int] = None,
    student_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get learning improvement recommendations"""
    try:
        recommendations = []
        
        if lecture_id:
            # Lecture-specific recommendations
            lecture_recs = _get_lecture_recommendations(lecture_id, db)
            recommendations.extend(lecture_recs)
        
        if student_id:
            # Student-specific recommendations
            student_recs = _get_student_recommendations(student_id, db)
            recommendations.extend(student_recs)
        
        if not lecture_id and not student_id:
            # General recommendations
            general_recs = _get_general_recommendations(db)
            recommendations.extend(general_recs)
        
        return {"recommendations": recommendations}
        
    except Exception as e:
        logger.error(f"Recommendations retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


def _get_lecture_recommendations(lecture_id: int, db: Session) -> List[Dict[str, Any]]:
    """Generate lecture-specific recommendations"""
    recommendations = []
    
    # Identify questions with low correct rates
    low_performance_questions = db.query(Question).filter(
        and_(
            Question.lecture_id == lecture_id,
            Question.correct_rate < 50,
            Question.correct_rate.isnot(None)
        )
    ).all()
    
    if low_performance_questions:
        recommendations.append({
            "type": "content_review",
            "priority": "high",
            "title": "Areas requiring content review",
            "description": f"{len(low_performance_questions)} questions have correct rates below 50%. It is recommended to review the content of the relevant slides.",
            "action_items": [
                "Review questions with low correct rates",
                "Provide detailed explanations for related slide content",
                "Provide additional examples and practice problems"
            ]
        })
    
    return recommendations


def _get_student_recommendations(student_id: str, db: Session) -> List[Dict[str, Any]]:
    """Generate student-specific recommendations"""
    recommendations = []
    
    # Student weakness analysis
    weak_difficulties = db.query(
        Question.difficulty,
        func.avg(func.cast(StudentResponse.is_correct, func.Integer)).label('avg_correct')
    ).join(StudentResponse).filter(
        StudentResponse.student_id == student_id
    ).group_by(Question.difficulty).having(
        func.avg(func.cast(StudentResponse.is_correct, func.Integer)) < 0.6
    ).all()
    
    if weak_difficulties:
        difficulty_names = [diff.value for diff, _ in weak_difficulties]
        recommendations.append({
            "type": "skill_improvement",
            "priority": "medium",
            "title": "Difficulty levels requiring reinforcement",
            "description": f"Struggling with the following difficulty levels: {', '.join(difficulty_names)}",
            "action_items": [
                "Review basic concepts",
                "Practice with gradual difficulty increases",
                "Check related reference materials"
            ]
        })
    
    return recommendations


def _get_general_recommendations(db: Session) -> List[Dict[str, Any]]:
    """Generate general recommendations"""
    recommendations = []
    
    # Overall trend analysis
    avg_correct_rate = db.query(func.avg(Question.correct_rate)).filter(
        Question.correct_rate.isnot(None)
    ).scalar()
    
    if avg_correct_rate and avg_correct_rate < 70:
        recommendations.append({
            "type": "general_improvement",
            "priority": "high",
            "title": "Overall understanding improvement needed",
            "description": f"The overall average correct rate is low at {avg_correct_rate:.1f}%.",
            "action_items": [
                "Strengthen basic concepts",
                "Adjust question difficulty levels",
                "Provide additional explanatory materials"
            ]
        })
    
    return recommendations