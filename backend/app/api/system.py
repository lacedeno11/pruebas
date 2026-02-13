"""
System API Endpoints

Provides system health monitoring, agent logging, OT synchronization,
and dashboard statistics.

Endpoints:
- GET /system/health - Health check with mode indicator
- GET /system/logs - Paginated agent logs with filtering
- POST /system/sync-ots - Trigger OT ingestion from TELCOS API
- GET /system/stats - Dashboard statistics and metrics
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_api_client, get_db_session
from app.core.config import settings
from app.models import LogAgente, OT
from app.schemas import LogAgenteResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint with system status.
    
    Returns:
        Dict with status, mode, and timestamp
    """
    return {
        "status": "ok",
        "mode": settings.SYSTEM_MODE,
        "message": "DERCAS PEI API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs": {
            "swagger": "/api/v1/docs",
            "redoc": "/api/v1/redoc",
        },
    }


@router.get("/logs", response_model=dict)
async def get_logs(
    agente_name: Optional[str] = None,
    resultado: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    days: int = 7,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get paginated agent logs with filtering.
    
    Query Parameters:
        agente_name: Filter by agent name (ROUTER, OTS, PLANIFICACION, GOBERNANZA, COMUNICACION)
        resultado: Filter by result (SUCCESS, FAILURE, PENDING)
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        days: Days to include (default 7)
    
    Returns:
        Dict with paginated logs and metadata
    """
    # Calculate date range
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Build base query
    query = select(LogAgente).where(LogAgente.created_at >= cutoff_date)
    
    # Apply filters
    if agente_name:
        query = query.where(LogAgente.agente_name == agente_name)
    
    if resultado:
        query = query.where(LogAgente.resultado == resultado)
    
    # Count total before pagination
    count_query = select(func.count(LogAgente.id)).where(
        LogAgente.created_at >= cutoff_date
    )
    if agente_name:
        count_query = count_query.where(LogAgente.agente_name == agente_name)
    if resultado:
        count_query = count_query.where(LogAgente.resultado == resultado)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    skip = (page - 1) * page_size
    query = query.order_by(LogAgente.created_at.desc()).offset(skip).limit(page_size)
    
    result = await session.execute(query)
    logs = result.scalars().all()
    
    return {
        "status": "success",
        "items": [LogAgenteResponse.from_orm(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("/sync-ots", status_code=status.HTTP_200_OK)
async def sync_ots(
    session: AsyncSession = Depends(get_db_session),
    api_client=Depends(get_api_client),
) -> dict:
    """
    Trigger OT ingestion from TELCOS API.
    
    Fetches OTs from external TELCOS API or uses mock data based on SYSTEM_MODE.
    Creates OT records in database for unprocessed orders.
    
    Returns:
        Dict with ingestion summary and statistics
    """
    try:
        # Get OTs from API client (mock or production)
        ots_data = await api_client.get_ots_from_telcos(page=1, limit=100)
        
        if not ots_data or not isinstance(ots_data, list):
            return {
                "status": "error",
                "message": "Failed to fetch OTs from API",
                "ingested_count": 0,
                "skipped_count": 0,
                "error_geo_count": 0,
            }
        
        ingested_count = 0
        skipped_count = 0
        error_geo_count = 0
        
        # Process each OT
        for ot_data in ots_data:
            # Check if OT already exists
            existing = await session.execute(
                select(OT).where(OT.external_id == ot_data.get("external_id"))
            )
            
            if existing.scalar_one_or_none():
                skipped_count += 1
                continue
            
            # Create new OT record
            status = "PREPLANIFICADA"
            
            # Check for missing coordinates (ERROR_GEO)
            if not ot_data.get("lat") or not ot_data.get("long"):
                status = "ERROR_GEO"
                error_geo_count += 1
            
            new_ot = OT(
                external_id=ot_data.get("external_id"),
                status=status,
                project_type=ot_data.get("project_type", "PUBLICO"),
                cliente_id=ot_data.get("cliente_id"),
                login=ot_data.get("login"),
                lat=ot_data.get("lat"),
                long=ot_data.get("long"),
            )
            
            session.add(new_ot)
            ingested_count += 1
        
        await session.commit()
        
        return {
            "status": "success",
            "message": f"OT synchronization completed successfully",
            "ingested_count": ingested_count,
            "skipped_count": skipped_count,
            "error_geo_count": error_geo_count,
            "total_processed": ingested_count + skipped_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    except Exception as e:
        await session.rollback()
        return {
            "status": "error",
            "message": f"Sync failed: {str(e)}",
            "ingested_count": 0,
            "skipped_count": 0,
            "error_geo_count": 0,
        }


@router.get("/stats")
async def get_stats(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get dashboard statistics and metrics.
    
    Returns:
        Dict with comprehensive system statistics
    """
    try:
        # OT counts by status
        status_query = select(OT.status, func.count(OT.id)).group_by(OT.status)
        status_result = await session.execute(status_query)
        status_counts = {row[0]: row[1] for row in status_result.fetchall()}
        
        # Total OTs
        total_query = select(func.count(OT.id))
        total_result = await session.execute(total_query)
        total_ots = total_result.scalar()
        
        # OT project type distribution
        project_type_query = select(OT.project_type, func.count(OT.id)).group_by(OT.project_type)
        project_result = await session.execute(project_type_query)
        project_counts = {row[0]: row[1] for row in project_result.fetchall()}
        
        # Inactivity alert count (>48h in PREPLANIFICADA)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=48)
        inactivity_query = select(func.count(OT.id)).where(
            OT.status == "PREPLANIFICADA",
            OT.created_at < cutoff_time,
        )
        inactivity_result = await session.execute(inactivity_query)
        inactivity_count = inactivity_result.scalar()
        
        # Detention alert count (>20 days in DETENIDA)
        detention_cutoff = datetime.now(timezone.utc) - timedelta(days=20)
        detention_query = select(func.count(OT.id)).where(
            OT.status == "DETENIDA",
            OT.detention_date.isnot(None),
            OT.detention_date < detention_cutoff,
        )
        detention_result = await session.execute(detention_query)
        detention_count = detention_result.scalar()
        
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ots": {
                "total": total_ots,
                "by_status": status_counts,
                "by_project_type": project_counts,
            },
            "alerts": {
                "inactivity_count": inactivity_count or 0,
                "detention_warning_count": detention_count or 0,
                "error_geo_count": status_counts.get("ERROR_GEO", 0),
            },
            "mode": settings.SYSTEM_MODE,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Statistics error: {str(e)}",
        )


__all__ = ["router"]


