"""
Answer model for storing correct answers and explanations
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class Answer(BaseModel):
    """Model for managing answer information"""
    __tablename__ = "answers"
    
    # Basic information
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, comment="Question ID")
    
    # Answer content
    answer_text = Column(Text, nullable=False, comment="Answer content")
    is_correct = Column(Boolean, nullable=False, comment="Correct answer flag")
    explanation = Column(Text, nullable=True, comment="Explanation")
    
    # Metadata
    order_index = Column(Integer, nullable=True, comment="Choice order (for multiple choice questions)")
    keywords = Column(Text, nullable=True, comment="Related keywords (comma-separated)")
    
    # Relationships
    question = relationship("Question", back_populates="answers")
    
    def __repr__(self):
        return f"<Answer(id={self.id}, question_id={self.question_id}, is_correct={self.is_correct})>"
    
    def to_dict(self):
        """Return as dictionary format"""
        return {
            "id": self.id,
            "question_id": self.question_id,
            "answer_text": self.answer_text,
            "is_correct": self.is_correct,
            "explanation": self.explanation,
            "order_index": self.order_index,
            "keywords": self.keywords.split(",") if self.keywords else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }