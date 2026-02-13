"""FastAPI Application Entry Point for PEI Platform"""

import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.config.settings import settings
from backend.database.session import get_db
from backend.api.routes import ots, cuadrillas, agents, mock
from backend.agents.gobernanza_agent import GobernanzaAgent
from backend.agents.planificacion_agent import PlanificacionAgent
from backend.services.notification_service import NotificationService
from backend.services.telcos_service import TelcosService

logger = logging.getLogger(__name__)

# WebSocket connection manager for broadcasting OT updates
class ConnectionManager:
    """Manager for WebSocket connections"""

    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Add a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(
            f"WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(
            f"WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {str(e)}")
                disconnected.add(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global connection manager instance
manager = ConnectionManager()

# APScheduler scheduler instance
scheduler = AsyncIOScheduler()


# Scheduler job functions
async def governance_daily_check():
    """Daily governance check at 00:30 - alerts and auto-cancellation"""
    logger.info("Starting governance_daily_check job...")
    try:
        db = next(get_db())
        try:
            notification_service = NotificationService()
            gobernanza_agent = GobernanzaAgent(
                db_session=db,
                notification_service=notification_service,
            )
            result = await gobernanza_agent.check_inactivity()
            logger.info(
                f"Governance check completed: {result.alerts_sent} alerts sent, "
                f"{result.ots_cancelled} OTs cancelled"
            )

            # Broadcast to WebSocket clients
            await manager.broadcast(
                {
                    "type": "governance_check_complete",
                    "alerts_sent": result.alerts_sent,
                    "ots_cancelled": result.ots_cancelled,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in governance_daily_check: {str(e)}")


async def route_optimization():
    """Nightly route optimization at 00:00 - normalize all routes"""
    logger.info("Starting route_optimization job...")
    try:
        db = next(get_db())
        try:
            planificacion_agent = PlanificacionAgent(
                db_session=db,
                llm_client=None,  # Not needed for normalize_routes
            )
            result = await planificacion_agent.normalize_routes()
            logger.info(
                f"Route optimization completed: {result.total_assigned} "
                f"assignments optimized"
            )

            # Broadcast to WebSocket clients
            await manager.broadcast(
                {
                    "type": "route_optimization_complete",
                    "total_assignments": result.total_assigned,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in route_optimization: {str(e)}")


async def inactivity_alert_check():
    """Hourly inactivity check - alerts for OTs in PREPLANIFICADA > 48h"""
    logger.info("Starting inactivity_alert_check job...")
    try:
        db = next(get_db())
        try:
            notification_service = NotificationService()
            gobernanza_agent = GobernanzaAgent(
                db_session=db,
                notification_service=notification_service,
            )
            result = await gobernanza_agent.check_preplanificada_inactivity()
            logger.info(
                f"Inactivity check completed: {result.alerts_sent} alerts sent"
            )

            # Broadcast to WebSocket clients if alerts were sent
            if result.alerts_sent > 0:
                await manager.broadcast(
                    {
                        "type": "inactivity_alert",
                        "alerts_sent": result.alerts_sent,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in inactivity_alert_check: {str(e)}")


async def stats_update():
    """Periodic stats cache update - every 15 minutes"""
    logger.info("Stats cache update job running...")
    # This is a placeholder - actual stats caching would be implemented
    # in the stats route with functools.lru_cache or similar
    logger.debug("Stats cache updated")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Context manager for application startup and shutdown"""
    # Startup
    logger.info("Starting PEI Platform API...")
    scheduler.start()

    # Add scheduled jobs
    scheduler.add_job(
        governance_daily_check,
        "cron",
        hour=0,
        minute=30,
        id="governance_daily_check",
        name="Daily Governance Check",
    )

    scheduler.add_job(
        route_optimization,
        "cron",
        hour=0,
        minute=0,
        id="route_optimization",
        name="Nightly Route Optimization",
    )

    scheduler.add_job(
        inactivity_alert_check,
        "interval",
        hours=1,
        id="inactivity_alert_check",
        name="Hourly Inactivity Check",
    )

    scheduler.add_job(
        stats_update,
        "interval",
        minutes=15,
        id="stats_update",
        name="Stats Cache Update",
    )

    logger.info("Scheduled jobs registered")

    # Validate API connection
    try:
        telcos_service = TelcosService()
        is_connected = await telcos_service.validate_api_connection()
        if is_connected:
            logger.info(
                f"TELCOS API connection validated "
                f"(Mode: {settings.SYSTEM_MODE})"
            )
        else:
            logger.warning(
                f"TELCOS API connection failed "
                f"(Mode: {settings.SYSTEM_MODE})"
            )
    except Exception as e:
        logger.warning(f"Error validating TELCOS API connection: {str(e)}")

    yield

    # Shutdown
    logger.info("Shutting down PEI Platform API...")
    scheduler.shutdown()
    logger.info("Scheduler shut down successfully")


# Create FastAPI application
app = FastAPI(
    title="PEI Platform API",
    version="1.0.0",
    description="Agentic Work Order Management System for TELCONET",
    lifespan=lifespan,
)

# Configure CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint returning API info and health status"""
    return {
        "name": "PEI Platform API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "mode": settings.SYSTEM_MODE,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


# WebSocket endpoint for real-time OT updates
@app.websocket("/ws/ots")
async def websocket_ots_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time OT updates.

    Clients connect here to receive real-time notifications about:
    - OT status changes
    - New OT creation
    - Assignment updates
    - Governance actions
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_text()
            logger.debug(f"WebSocket message received: {data}")

            # Echo back or process client messages if needed
            await websocket.send_json(
                {
                    "type": "pong",
                    "message": "Message received",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket connection closed by client")

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)


# Include routers
app.include_router(ots.router, prefix="/api", tags=["OTs"])
app.include_router(cuadrillas.router, prefix="/api", tags=["Cuadrillas"])
app.include_router(agents.router, prefix="/api", tags=["Agents"])

# Include mock router only in MOCK mode
if settings.SYSTEM_MODE == "MOCK":
    app.include_router(mock.router, prefix="/api", tags=["Mock APIs"])
    logger.info("Mock API routes enabled (SYSTEM_MODE=MOCK)")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
    )

