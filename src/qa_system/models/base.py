"""
Base database model configuration
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime
from src.qa_system.config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # SQL query log output
    pool_pre_ping=True
)

# Session configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Metadata configuration
metadata = MetaData()

# Create base class
Base = declarative_base(metadata=metadata)


class BaseModel(Base):
    """Base class for all models"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


# Database session dependency injection
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database initialization
def init_db():
    """Initialize database"""
    Base.metadata.create_all(bind=engine)


# Database reset (for development)
def reset_db():
    """Reset database (for development)"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)