"""Main FastAPI application for PEI Agéntico Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database.db import init_db
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize FastAPI application
app = FastAPI(
    title="PEI Agéntico Platform",
    version="1.0.0",
    description="LangGraph-based Work Order Management System for Field Operations",
)

# Configure CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
cors_origins = [origin.strip() for origin in cors_origins]  # Remove whitespace

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    init_db()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# System information endpoint
@app.get("/api/system/info")
async def system_info():
    """Get system information and configuration."""
    return {
        "mode": os.getenv("SYSTEM_MODE", "MOCK"),
        "version": "1.0.0",
        "database": os.getenv("DATABASE_URL", "sqlite:///./pei.db"),
        "llm_model": os.getenv("LLM_MODEL", "gpt-4"),
    }


# Mount routers from routes module
from backend.api.routes import ots, cuadrillas, planning, validation, chat

app.include_router(ots.router, prefix="/api", tags=["OTs"])
app.include_router(cuadrillas.router, prefix="/api", tags=["Cuadrillas"])
app.include_router(planning.router, prefix="/api", tags=["Planning"])
app.include_router(validation.router, prefix="/api", tags=["Validation"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


