import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core import settings, Base, engine, get_db
from backend.app.utils.scheduler import setup_scheduler

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown events.
    """
    global scheduler
    
    # Startup
    logger.info("Starting PEI Platform - DERCAS TO-BE AGÉNTICO")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Setup and start scheduler
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down PEI Platform")
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")


# Create FastAPI application
app = FastAPI(
    title="PEI Platform - DERCAS TO-BE AGÉNTICO",
    version="1.0.0",
    description="Plataforma de Coordinación de Equipos de Instalación - DERCAS TO-BE AGÉNTICO",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include router (after app creation to avoid circular imports)
from backend.app.api.routes import router as api_router

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """
    Root endpoint for health check.
    
    Returns:
        Dictionary with status and system mode information
    """
    return {
        "status": "ok",
        "system_mode": settings.SYSTEM_MODE,
        "title": "PEI Platform - DERCAS TO-BE AGÉNTICO",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

