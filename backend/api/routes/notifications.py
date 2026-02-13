"""
Notification endpoints for sending and managing alerts.
Supports Telegram and Email channels via ComunicacionAgent.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.base import get_db
from backend.database import schemas, models
from backend.services.notification_service import NotificationService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Initialize service
notification_service = NotificationService()


# ============================================================================
# GET Endpoints
# ============================================================================


@router.get("/history", response_model=List[schemas.LogAgenteResponse])
async def get_notification_history(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
):
    """
    Get history of sent notifications.
    
    Query Parameters:
    - agent_name: Filter by agent name (e.g., 'ComunicacionAgent')
    - date_from: Start date for filtering (format: YYYY-MM-DD)
    - date_to: End date for filtering (format: YYYY-MM-DD)
    - skip: Pagination offset
    - limit: Maximum number of results
    
    Returns:
        List of notification log entries
    """
    try:
        query = db.query(models.LogAgente).filter(
            models.LogAgente.agente_name.like("%Comunicacion%")
        )
        
        # Apply filters
        if agent_name:
            query = query.filter(models.LogAgente.agente_name == agent_name)
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(models.LogAgente.created_at >= from_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_from format. Use YYYY-MM-DD",
                )
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(models.LogAgente.created_at < to_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date_to format. Use YYYY-MM-DD",
                )
        
        # Execute query with pagination
        logs = query.order_by(models.LogAgente.created_at.desc()).offset(skip).limit(limit).all()
        return logs
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notification history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching notification history",
        )


# ============================================================================
# POST Endpoints
# ============================================================================


@router.post("/telegram", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def send_telegram_notification(
    request: schemas.TelegramNotificationRequest,
    db: Session = Depends(get_db),
):
    """
    Send a Telegram notification to a specific chat.
    
    Request Body:
    - chat_id: Telegram chat ID
    - message: Message text
    
    Returns:
        Notification delivery confirmation
    """
    try:
        # Send notification asynchronously
        # TODO: Integrate with ComunicacionAgent or call notification_service directly
        
        # For now, create a log entry
        log = models.LogAgente(
            agente_name="ComunicacionAgent",
            accion=f"Send Telegram to chat {request.chat_id}",
            resultado="queued",
            raw_llm_response=request.message,
        )
        db.add(log)
        db.commit()
        
        logger.info(f"Queued Telegram notification to {request.chat_id}")
        
        return {
            "success": True,
            "message": "Notification queued for delivery",
            "channel": "telegram",
            "recipient": request.chat_id,
            "log_id": log.id,
        }
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending Telegram notification",
        )


@router.post("/email", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def send_email_notification(
    request: schemas.EmailNotificationRequest,
    db: Session = Depends(get_db),
):
    """
    Send an email notification.
    
    Request Body:
    - to_email: Recipient email address
    - subject: Email subject
    - body: Email body
    
    Returns:
        Email delivery confirmation
    """
    try:
        # Send email asynchronously
        # TODO: Integrate with ComunicacionAgent or call notification_service directly
        
        # For now, create a log entry
        log = models.LogAgente(
            agente_name="ComunicacionAgent",
            accion=f"Send Email to {request.to_email}",
            resultado="queued",
            raw_llm_response=f"Subject: {request.subject}\n\n{request.body}",
        )
        db.add(log)
        db.commit()
        
        logger.info(f"Queued email notification to {request.to_email}")
        
        return {
            "success": True,
            "message": "Email queued for delivery",
            "channel": "email",
            "recipient": request.to_email,
            "log_id": log.id,
        }
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending email notification",
        )


@router.post("/test", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def send_test_notification(
    request: schemas.NotificationTestRequest,
    db: Session = Depends(get_db),
):
    """
    Send a test notification to verify channel configuration.
    
    Request Body:
    - channel: Notification channel ('telegram' or 'email')
    - recipient: Recipient identifier (chat_id for Telegram, email for Email)
    
    Returns:
        Test notification confirmation
    """
    try:
        if request.channel == "telegram":
            log = models.LogAgente(
                agente_name="ComunicacionAgent",
                accion=f"Send Test Telegram to {request.recipient}",
                resultado="queued",
                raw_llm_response="Test message: If you see this, Telegram notifications are working!",
            )
        elif request.channel == "email":
            log = models.LogAgente(
                agente_name="ComunicacionAgent",
                accion=f"Send Test Email to {request.recipient}",
                resultado="queued",
                raw_llm_response="Test email: If you see this, email notifications are working!",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid channel. Must be 'telegram' or 'email'",
            )
        
        db.add(log)
        db.commit()
        
        logger.info(f"Queued test {request.channel} notification to {request.recipient}")
        
        return {
            "success": True,
            "message": f"Test {request.channel} notification queued",
            "channel": request.channel,
            "recipient": request.recipient,
            "log_id": log.id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending test notification",
        )

