"""
Main FastAPI application
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import logging
from pathlib import Path

from src.qa_system.config import settings
from src.qa_system.models.base import init_db
from .routers import lectures, questions, analytics

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="QA System",
    description="AI-powered Q&A generation system for lecture content",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and template configuration
static_dir = Path(__file__).parent.parent / "static"
templates_dir = Path(__file__).parent.parent / "templates"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Jinja2Templates(directory=str(templates_dir))

# Register routers
app.include_router(lectures.router, prefix="/api/lectures", tags=["lectures"])
app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])


@app.on_event("startup")
async def startup_event():
    """Process to run at application startup"""
    logger.info("Starting QA System...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    logger.info("QA System startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Process to run at application shutdown"""
    logger.info("Shutting down QA System...")


@app.get("/")
async def read_root(request: Request):
    """Homepage"""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "title": "QA System"}
    )


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "debug": settings.debug
    }


@app.get("/lectures")
async def lectures_page(request: Request):
    """Lecture list page"""
    return templates.TemplateResponse(
        "lectures.html",
        {"request": request, "title": "Lecture List"}
    )


@app.get("/questions")
async def questions_page(request: Request):
    """Question list page"""
    return templates.TemplateResponse(
        "questions.html",
        {"request": request, "title": "Question List"}
    )


@app.get("/analytics")
async def analytics_page(request: Request):
    """Analytics page"""
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "title": "Comprehension Analytics"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )