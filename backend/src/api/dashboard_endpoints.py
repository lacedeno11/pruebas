"""
Dashboard API endpoints for PEI Platform.

Provides REST API endpoints for frontend analytics and visualization:
- Key metrics (OT counts, planning rate, utilization)
- Kanban board data grouped by status
- Map visualization data with coordinates
- Active governance alerts
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Cuadrilla, OT, OTStatus, ProjectType, AgentLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# Pydantic schemas for request/response
from pydantic import BaseModel
from typing import List, Dict, Any


class MetricsResponse(BaseModel):
    """Response schema for dashboard metrics"""

    total_ots: int
    ots_by_status: Dict[str, int]
    ots_by_project_type: Dict[str, int]
    cuadrilla_utilization_percentage: float
    geo_error_count: int
    average_planning_time_hours: float
    timestamp: datetime


class OTCardData(BaseModel):
    """OT card data for Kanban view"""

    id: int
    external_id: str
    project_type: str
    cuadrilla_name: Optional[str] = None
    cliente_id: str
    is_geo_error: bool


class KanbanStatusData(BaseModel):
    """Kanban column data"""

    status: str
    count: int
    ots: List[OTCardData]


class KanbanResponse(BaseModel):
    """Response schema for Kanban data"""

    columns: Dict[str, KanbanStatusData]
    total_ots: int
    timestamp: datetime


class LocationData(BaseModel):
    """Location data for OT or Cuadrilla"""

    id: int
    type: str  # "ot" or "cuadrilla"
    name: str
    latitude: float
    longitude: float
    metadata: Dict[str, Any] = {}


class MapResponse(BaseModel):
    """Response schema for map visualization data"""

    ots: List[LocationData]
    cuadrillas: List[LocationData]
    center: tuple[float, float] = (-1.8312, -78.1834)
    zoom: int = 7
    timestamp: datetime


class AlertData(BaseModel):
    """Alert data"""

    id: int
    type: str  # "detention", "preplanificada", "missing_docs"
    ot_id: Optional[int] = None
    severity: str  # "warning", "critical"
    message: str
    details: Dict[str, Any] = {}
    created_at: datetime


class AlertsResponse(BaseModel):
    """Response schema for alerts"""

    active_alerts: List[AlertData]
    total_critical: int
    total_warnings: int
    timestamp: datetime


@router.get("/metrics", response_model=MetricsResponse)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """
    Get key dashboard metrics.

    Returns:
    - total_ots: Total number of OTs in system
    - ots_by_status: Count of OTs for each status
    - ots_by_project_type: Count of OTs for each project type
    - cuadrilla_utilization_percentage: Overall capacity utilization
    - geo_error_count: Number of OTs with geographic errors
    - average_planning_time_hours: Average time from PREPLANIFICADA to PLANIFICADA

    Returns:
        MetricsResponse: Dashboard metrics
    """
    try:
        # Get all OTs
        result = await db.execute(select(OT))
        all_ots = result.scalars().all()
        total_ots = len(all_ots)

        # Count by status
        ots_by_status = {}
        for status in OTStatus:
            count = len([ot for ot in all_ots if ot.status == status])
            ots_by_status[status.value] = count

        # Count by project type
        ots_by_project_type = {}
        for proj_type in ProjectType:
            count = len([ot for ot in all_ots if ot.project_type == proj_type])
            ots_by_project_type[proj_type.value] = count

        # Calculate cuadrilla utilization
        cuad_result = await db.execute(select(Cuadrilla))
        cuadrillas = cuad_result.scalars().all()
        total_capacity = sum(c.max_daily_capacity for c in cuadrillas) or 1
        used_capacity = sum(c.current_load for c in cuadrillas)
        cuadrilla_utilization_percentage = (used_capacity / total_capacity * 100) if total_capacity > 0 else 0

        # Count geo errors
        geo_error_count = len([ot for ot in all_ots if ot.is_geo_error])

        # Calculate average planning time
        # OTs that have transitioned from PREPLANIFICADA to at least PLANIFICADA
        planned_ots = [ot for ot in all_ots if ot.status != OTStatus.PREPLANIFICADA and ot.assigned_at]
        average_planning_time_hours = 0
        if planned_ots:
            total_hours = sum(
                (ot.assigned_at - ot.created_at).total_seconds() / 3600
                for ot in planned_ots
                if ot.assigned_at and ot.created_at
            )
            average_planning_time_hours = total_hours / len(planned_ots) if planned_ots else 0

        logger.info(
            f"Dashboard metrics: {total_ots} OTs, "
            f"utilization {cuadrilla_utilization_percentage:.1f}%, "
            f"{geo_error_count} geo errors"
        )

        return MetricsResponse(
            total_ots=total_ots,
            ots_by_status=ots_by_status,
            ots_by_project_type=ots_by_project_type,
            cuadrilla_utilization_percentage=cuadrilla_utilization_percentage,
            geo_error_count=geo_error_count,
            average_planning_time_hours=average_planning_time_hours,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting dashboard metrics")


@router.get("/kanban", response_model=KanbanResponse)
async def get_kanban_data(
    db: AsyncSession = Depends(get_db),
) -> KanbanResponse:
    """
    Get OTs grouped by status for Kanban board view.

    Returns OTs organized by their current status, including:
    - id: OT ID
    - external_id: External system ID
    - project_type: PUBLICO, PRIVADO, TERCERIZADO
    - cuadrilla_name: Name of assigned cuadrilla (if assigned)
    - cliente_id: Client identifier
    - is_geo_error: Whether OT has geographic error

    Returns:
        KanbanResponse: Kanban board data with columns for each status
    """
    try:
        # Get all OTs with cuadrilla relationships
        result = await db.execute(
            select(OT).options(joinedload(OT.cuadrilla))
        )
        all_ots = result.scalars().all()

        # Group OTs by status
        columns = {}
        for status in OTStatus:
            status_ots = [ot for ot in all_ots if ot.status == status]
            ot_cards = [
                OTCardData(
                    id=ot.id,
                    external_id=ot.external_id,
                    project_type=ot.project_type.value,
                    cuadrilla_name=ot.cuadrilla.name if ot.cuadrilla else None,
                    cliente_id=ot.cliente_id,
                    is_geo_error=ot.is_geo_error,
                )
                for ot in status_ots
            ]

            columns[status.value] = KanbanStatusData(
                status=status.value,
                count=len(status_ots),
                ots=ot_cards,
            )

        logger.info(f"Kanban data retrieved: {len(all_ots)} OTs across {len(columns)} statuses")

        return KanbanResponse(
            columns=columns,
            total_ots=len(all_ots),
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error getting kanban data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting kanban data")


@router.get("/map", response_model=MapResponse)
async def get_map_data(
    db: AsyncSession = Depends(get_db),
) -> MapResponse:
    """
    Get OTs and Cuadrillas with coordinates for map visualization.

    Returns:
    - OTs: Points with status color coding and project type indicators
    - Cuadrillas: Centroid locations with 10km radius circles
    - Map center: Ecuador center coordinates [-1.8312, -78.1834]
    - Zoom level: 7 (suitable for Ecuador)

    Returns:
        MapResponse: Map visualization data with all OT and Cuadrilla locations
    """
    try:
        # Get OTs with coordinates
        ot_result = await db.execute(
            select(OT).where((OT.lat.isnot(None)) & (OT.long.isnot(None)))
        )
        ots = ot_result.scalars().all()

        ot_locations = [
            LocationData(
                id=ot.id,
                type="ot",
                name=ot.external_id,
                latitude=ot.lat,
                longitude=ot.long,
                metadata={
                    "status": ot.status.value,
                    "project_type": ot.project_type.value,
                    "cliente_id": ot.cliente_id,
                    "cuadrilla_id": ot.cuadrilla_id,
                    "is_geo_error": ot.is_geo_error,
                },
            )
            for ot in ots
        ]

        # Get Cuadrillas with centroids
        cuad_result = await db.execute(
            select(Cuadrilla).where(
                (Cuadrilla.last_centroid_lat.isnot(None))
                & (Cuadrilla.last_centroid_long.isnot(None))
            )
        )
        cuadrillas = cuad_result.scalars().all()

        cuadrilla_locations = [
            LocationData(
                id=c.id,
                type="cuadrilla",
                name=c.name,
                latitude=c.last_centroid_lat,
                longitude=c.last_centroid_long,
                metadata={
                    "type": c.type.value,
                    "current_load": c.current_load,
                    "max_capacity": c.max_daily_capacity,
                    "utilization": c.current_load / c.max_daily_capacity if c.max_daily_capacity > 0 else 0,
                },
            )
            for c in cuadrillas
        ]

        logger.info(f"Map data retrieved: {len(ot_locations)} OTs, {len(cuadrilla_locations)} Cuadrillas")

        return MapResponse(
            ots=ot_locations,
            cuadrillas=cuadrilla_locations,
            center=(-1.8312, -78.1834),
            zoom=7,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error getting map data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting map data")


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity (warning or critical)"),
    ot_id: Optional[int] = Query(None, description="Filter by OT ID"),
    db: AsyncSession = Depends(get_db),
) -> AlertsResponse:
    """
    Get active governance alerts.

    Returns alerts for:
    - Detention: OTs in DETENIDA status for >20 days
    - Preplanificada: OTs in PREPLANIFICADA status for >48 hours
    - Missing Docs: PUBLICO projects without 29 TelcoDrive documents

    Query Parameters:
    - severity: Filter by severity (warning or critical)
    - ot_id: Filter by specific OT

    Returns:
        AlertsResponse: Active alerts with counts
    """
    try:
        alerts = []
        now = datetime.utcnow()

        # Get all OTs for alert checking
        result = await db.execute(select(OT))
        all_ots = result.scalars().all()

        # Check for detention alerts (OTs in DETENIDA status)
        detenida_ots = [ot for ot in all_ots if ot.status == OTStatus.DETENIDA]
        for ot in detenida_ots:
            if ot.assigned_at:
                days_in_detention = (now - ot.assigned_at).days
                if days_in_detention >= 20:
                    severity_level = "critical" if days_in_detention >= 29 else "warning"
                    alerts.append(
                        AlertData(
                            id=len(alerts),
                            type="detention",
                            ot_id=ot.id,
                            severity=severity_level,
                            message=f"OT {ot.external_id} detained for {days_in_detention} days",
                            details={
                                "days_detained": days_in_detention,
                                "reason": ot.detention_reason or "Not specified",
                            },
                            created_at=ot.updated_at,
                        )
                    )

        # Check for PREPLANIFICADA alerts (>48 hours without assignment)
        preplanificada_ots = [ot for ot in all_ots if ot.status == OTStatus.PREPLANIFICADA]
        for ot in preplanificada_ots:
            hours_waiting = (now - ot.created_at).total_seconds() / 3600
            if hours_waiting > 48:
                alerts.append(
                    AlertData(
                        id=len(alerts),
                        type="preplanificada",
                        ot_id=ot.id,
                        severity="warning",
                        message=f"OT {ot.external_id} waiting for planning for {hours_waiting:.1f} hours",
                        details={
                            "hours_waiting": hours_waiting,
                            "cliente_id": ot.cliente_id,
                        },
                        created_at=ot.created_at,
                    )
                )

        # Check for missing documents (PUBLICO projects)
        # TODO: Integrate with TelcoDrive API to get actual document counts
        # For now, flag PUBLICO projects that are not yet FINALIZADA
        publico_ots = [ot for ot in all_ots if ot.project_type == ProjectType.PUBLICO and ot.status != OTStatus.FINALIZADA]
        for ot in publico_ots:
            alerts.append(
                AlertData(
                    id=len(alerts),
                    type="missing_docs",
                    ot_id=ot.id,
                    severity="warning",
                    message=f"PUBLICO OT {ot.external_id} requires 29 TelcoDrive documents before completion",
                    details={
                        "project_type": "PUBLICO",
                        "required_docs": 29,
                    },
                    created_at=ot.created_at,
                )
            )

        # Apply filters
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if ot_id:
            alerts = [a for a in alerts if a.ot_id == ot_id]

        # Count by severity
        critical_count = len([a for a in alerts if a.severity == "critical"])
        warning_count = len([a for a in alerts if a.severity == "warning"])

        logger.info(f"Alerts retrieved: {critical_count} critical, {warning_count} warnings")

        return AlertsResponse(
            active_alerts=alerts,
            total_critical=critical_count,
            total_warnings=warning_count,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Error getting alerts")

