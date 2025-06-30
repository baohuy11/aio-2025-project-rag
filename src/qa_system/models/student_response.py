"""
Student response model for storing student answers and analytics
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class StudentResponse(BaseModel):
    """Model for managing student response information"""
    __tablename__ = "student_responses"
    
    # Basic information
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, comment="Question ID")
    student_id = Column(String(100), nullable=False, comment="Student ID")
    
    # Response content
    response_text = Column(Text, nullable=False, comment="Student's response")
    is_correct = Column(Boolean, nullable=True, comment="Correct answer flag")
    score = Column(Float, nullable=True, comment="Score (0-100)")
    
    # Response time
    response_time = Column(Integer, nullable=True, comment="Response time (seconds)")
    submitted_at = Column(DateTime, server_default=func.now(), comment="Submission timestamp")
    
    # Metadata
    attempt_number = Column(Integer, default=1, comment="Attempt number")
    confidence_level = Column(Integer, nullable=True, comment="Confidence level (1-5)")
    difficulty_perception = Column(Integer, nullable=True, comment="Perceived difficulty (1-5)")
    
    # Session information
    session_id = Column(String(100), nullable=True, comment="Session ID")
    ip_address = Column(String(45), nullable=True, comment="IP address")
    user_agent = Column(String(500), nullable=True, comment="User agent")
    
    # Relationships
    question = relationship("Question", back_populates="student_responses")
    
    def __repr__(self):
        return f"<StudentResponse(id={self.id}, student_id='{self.student_id}', is_correct={self.is_correct})>"
    
    def to_dict(self):
        """Return as dictionary format"""
        return {
            "id": self.id,
            "question_id": self.question_id,
            "student_id": self.student_id,
            "response_text": self.response_text,
            "is_correct": self.is_correct,
            "score": self.score,
            "response_time": self.response_time,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "attempt_number": self.attempt_number,
            "confidence_level": self.confidence_level,
            "difficulty_perception": self.difficulty_perception,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def calculate_performance_metrics(self):
        """Calculate performance metrics"""
        metrics = {
            "accuracy": 1.0 if self.is_correct else 0.0,
            "response_efficiency": None,
            "confidence_accuracy_ratio": None
        }
        
        # Response efficiency (comparison with estimated time)
        if self.response_time and hasattr(self.question, 'estimated_time') and self.question.estimated_time:
            metrics["response_efficiency"] = self.question.estimated_time / self.response_time
        
        # Confidence and accuracy ratio
        if self.confidence_level and self.is_correct is not None:
            accuracy_score = 1.0 if self.is_correct else 0.0
            metrics["confidence_accuracy_ratio"] = accuracy_score / (self.confidence_level / 5.0)
        
        return metrics