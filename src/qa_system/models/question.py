"""
Question model for storing generated questions
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel


class QuestionType(str, Enum):
    """Question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    ESSAY = "essay"
    SHORT_ANSWER = "short_answer"


class DifficultyLevel(str, Enum):
    """Difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(BaseModel):
    """Model for managing question information"""
    __tablename__ = "questions"
    
    # Basic information
    lecture_id = Column(Integer, ForeignKey("lectures.id"), nullable=False, comment="Lecture ID")
    slide_number = Column(Integer, nullable=False, comment="Slide number")
    
    # Question content
    question_text = Column(Text, nullable=False, comment="Question text")
    question_type = Column(SQLEnum(QuestionType), nullable=False, comment="Question type")
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=False, comment="Difficulty level")
    
    # Correct answer information
    correct_answer = Column(Text, nullable=False, comment="Correct answer")
    explanation = Column(Text, nullable=True, comment="Explanation")
    
    # Choices (JSON format)
    choices = Column(JSON, nullable=True, comment="Choices (for multiple choice questions)")
    
    # Metadata
    keywords = Column(JSON, nullable=True, comment="Related keywords")
    estimated_time = Column(Integer, nullable=True, comment="Estimated answer time (seconds)")
    
    # Statistics
    usage_count = Column(Integer, default=0, comment="Usage count")
    correct_rate = Column(Integer, nullable=True, comment="Correct answer rate (%)")
    
    # Relationships
    lecture = relationship("Lecture", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
    student_responses = relationship("StudentResponse", back_populates="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Question(id={self.id}, type={self.question_type}, difficulty={self.difficulty})>"
    
    def to_dict(self):
        """Return as dictionary format"""
        return {
            "id": self.id,
            "lecture_id": self.lecture_id,
            "slide_number": self.slide_number,
            "question_text": self.question_text,
            "question_type": self.question_type.value,
            "difficulty": self.difficulty.value,
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "choices": self.choices,
            "keywords": self.keywords,
            "estimated_time": self.estimated_time,
            "usage_count": self.usage_count,
            "correct_rate": self.correct_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_multiple_choice(self) -> bool:
        """Check if it's a multiple choice question"""
        return self.question_type == QuestionType.MULTIPLE_CHOICE
    
    def is_essay_type(self) -> bool:
        """Check if it's an essay type question"""
        return self.question_type in [QuestionType.ESSAY, QuestionType.SHORT_ANSWER]
    
    def get_choices_list(self) -> list:
        """Get choices as a list"""
        if self.choices and isinstance(self.choices, list):
            return self.choices
        return []
    
    def get_keywords_list(self) -> list:
        """Get keywords as a list"""
        if self.keywords and isinstance(self.keywords, list):
            return self.keywords
        return []