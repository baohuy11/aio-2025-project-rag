"""
Lecture model for storing lecture information
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class Lecture(BaseModel):
    """Model for managing lecture information"""
    __tablename__ = "lectures"
    
    # Basic information
    title = Column(String(255), nullable=False, comment="Lecture title")
    description = Column(Text, nullable=True, comment="Lecture description")
    
    # File information
    original_filename = Column(String(255), nullable=False, comment="Original filename")
    file_path = Column(String(500), nullable=False, comment="File path")
    file_size = Column(Integer, nullable=False, comment="File size (bytes)")
    
    # Extracted content
    total_slides = Column(Integer, nullable=False, default=0, comment="Total number of slides")
    extracted_content = Column(Text, nullable=True, comment="Extracted content (JSON format)")
    
    # Processing status
    is_processed = Column(Boolean, default=False, nullable=False, comment="Processing completion flag")
    processing_status = Column(String(50), default="pending", comment="Processing status")
    error_message = Column(Text, nullable=True, comment="Error message")
    
    # Metadata
    author = Column(String(100), nullable=True, comment="Instructor name")
    subject = Column(String(100), nullable=True, comment="Subject name")
    lecture_date = Column(DateTime, nullable=True, comment="Lecture date and time")
    
    # Relationships
    questions = relationship("Question", back_populates="lecture", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lecture(id={self.id}, title='{self.title}', slides={self.total_slides})>"
    
    def to_dict(self):
        """Return as dictionary format"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "original_filename": self.original_filename,
            "total_slides": self.total_slides,
            "is_processed": self.is_processed,
            "processing_status": self.processing_status,
            "author": self.author,
            "subject": self.subject,
            "lecture_date": self.lecture_date.isoformat() if self.lecture_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }