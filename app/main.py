"""
AI Mock Interview System - Main Application
FastAPI application with database initialization and lifecycle management
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys

from app.database.postgres_db import engine, init_db, SessionLocal
from app.database.chroma_db import chroma_db
from app.database.models import Base
from app.services.question_service import QuestionService
from app.api.routes import router
from app.config import get_settings

# Get settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager
    Handles startup and shutdown events
    """
    # ============================================================
    # STARTUP
    # ============================================================
    logger.info("🚀 Starting AI Mock Interview API...")

    try:
        # Initialize PostgreSQL
        logger.info("Initializing PostgreSQL database...")
        init_db()
        logger.info("✓ PostgreSQL database initialized")

        # Check ChromaDB
        vector_count = chroma_db.get_collection_count()
        logger.info(f"✓ ChromaDB initialized with {vector_count} questions")

        # Load static questions if database is empty
        db = SessionLocal()
        try:
            from app.database.models import GlobalQuestion
            question_count = db.query(GlobalQuestion).filter(
                GlobalQuestion.is_static == 1
            ).count()

            if question_count == 0:
                logger.info("📚 Loading static questions from JSON...")
                try:
                    count = QuestionService.load_static_questions(
                        db,
                        "data/static_questions.json"
                    )
                    logger.info(f"✓ Loaded {count} static questions")
                except FileNotFoundError:
                    logger.warning("⚠ Static questions file not found. Skipping...")
                except Exception as e:
                    logger.error(f"❌ Error loading static questions: {e}")
            else:
                logger.info(f"✓ Found {question_count} existing static questions")

        except Exception as e:
            logger.error(f"❌ Error during startup: {e}")
        finally:
            db.close()

        logger.info("✅ AI Mock Interview API started successfully!")
        logger.info(f"📖 API Documentation: http://localhost:8000/docs")
        logger.info(f"🔍 Health Check: http://localhost:8000/api/{settings.API_VERSION}/health")

    except Exception as e:
        logger.critical(f"❌ CRITICAL: Failed to start application: {e}")
        raise

    yield

    # ============================================================
    # SHUTDOWN
    # ============================================================
    logger.info("🛑 Shutting down AI Mock Interview API...")
    logger.info("✓ Cleanup completed")


# Create FastAPI application
app = FastAPI(
    title="AI Mock Interview System",
    description="Backend API for conducting AI-powered mock interviews with intelligent question management",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(
    router,
    prefix=f"/api/{settings.API_VERSION}",
    tags=["AI Mock Interview"]
)


# Root endpoint
@app.get("/")
def root():
    """Root endpoint - API information"""
    return {
        "message": "AI Mock Interview System API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
        "health_check": f"/api/{settings.API_VERSION}/health"
    }


# Run with: uvicorn app.main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
