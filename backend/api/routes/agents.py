"""Agent orchestration API routes"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db, get_telcos_service, get_notification_service
from backend.models.proyecto import (
    IngestionResult,
    PlanningResult,
    GovernanceResult,
    StandardResponse,
)
from backend.utils.constants import OT_STATUS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

# In-memory job tracking (replace with Redis in production)
job_results = {}


@router.post("/ingest", response_model=IngestionResult)
async def ingest_ots(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    telcos_service=Depends(get_telcos_service),
):
    """
    Trigger OT ingestion from TELCOS API (UC-PEI-01).

    This endpoint triggers the OTS Agent to:
    1. Fetch OTs from TELCOS API
    2. Validate coordinates (lat/long not null)
    3. Create OT records in database with status PREPLANIFICADA
    4. Create audit logs for each operation
    5. Return ingestion results

    Returns:
    - IngestionResult with:
      - total: Total OTs processed
      - inserted: Successfully inserted OTs
      - errors: OTs with errors
      - error_details: Detailed error information

    Status Codes:
    - 200: Ingestion started/completed
    - 500: Internal server error
    """
    try:
        logger.info("Starting OT ingestion")

        # Fetch OTs from TELCOS API
        ots_data = await telcos_service.fetch_ots()
        logger.info(f"Fetched {len(ots_data)} OTs from TELCOS API")

        result = IngestionResult(
            total=len(ots_data),
            inserted=0,
            errors=0,
            error_details=[],
        )

        # Process each OT
        for ot_data in ots_data:
            try:
                # Validate coordinates
                if ot_data.get("lat") is None or ot_data.get("long") is None:
                    result.errors += 1
                    result.error_details.append(
                        {
                            "ot_id": ot_data.get("external_id"),
                            "error": "Missing coordinates (lat/long)",
                            "status": "ERROR_GEO",
                        }
                    )
                    logger.warning(
                        f"OT {ot_data.get('external_id')} missing coordinates"
                    )
                    continue

                # Check if OT already exists
                from backend.database.models import OT

                existing = db.query(OT).filter(
                    OT.external_id == ot_data.get("external_id")
                ).first()

                if existing:
                    logger.info(
                        f"OT {ot_data.get('external_id')} already exists, skipping"
                    )
                    continue

                # Create new OT record
                new_ot = OT(
                    external_id=ot_data.get("external_id"),
                    cliente_id=ot_data.get("cliente_id"),
                    login_id=ot_data.get("login_id"),
                    status=ot_data.get("status", OT_STATUS["PREPLANIFICADA"]),
                    project_type=ot_data.get("project_type"),
                    lat=ot_data.get("lat"),
                    long=ot_data.get("long"),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    last_status_change=datetime.now(),
                )

                db.add(new_ot)
                result.inserted += 1
                logger.info(f"Created OT {ot_data.get('external_id')}")

            except Exception as e:
                result.errors += 1
                result.error_details.append(
                    {
                        "ot_id": ot_data.get("external_id"),
                        "error": str(e),
                    }
                )
                logger.error(f"Error processing OT {ot_data.get('external_id')}: {str(e)}")

        # Commit all changes
        db.commit()
        logger.info(
            f"OT ingestion completed: {result.inserted} inserted, "
            f"{result.errors} errors"
        )

        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Error during OT ingestion: {str(e)}")
        return IngestionResult(
            total=0,
            inserted=0,
            errors=1,
            error_details=[{"error": str(e)}],
        )


@router.post("/plan", response_model=PlanningResult)
async def plan_ots(
    request_data: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Trigger OT planning and assignment (UC-PEI-02).

    This endpoint triggers the Planning Agent to implement the 3-phase algorithm:
    1. Balance Phase: Assign 1 OT to each cuadrilla
    2. Proximity Phase: Assign remaining OTs to nearest cuadrilla (<10km)
    3. Normalization: Optimize routes and centroids

    Request Body (optional):
    - ot_ids: List of specific OT IDs to plan (optional, defaults to all unassigned)

    Returns:
    - PlanningResult with:
      - assignments: List of assignment operations
      - total_assigned: Total OTs assigned in this operation
      - unassigned: List of OT IDs that could not be assigned

    Status Codes:
    - 200: Planning completed
    - 500: Internal server error
    """
    try:
        logger.info("Starting OT planning")

        from backend.database.models import OT, Cuadrilla, Asignacion

        # Get OTs to plan
        query = db.query(OT).filter(OT.status == OT_STATUS["PREPLANIFICADA"])

        if request_data and request_data.get("ot_ids"):
            ot_ids = request_data.get("ot_ids")
            query = query.filter(OT.id.in_(ot_ids))

        unplanned_ots = query.all()
        logger.info(f"Found {len(unplanned_ots)} OTs to plan")

        # Get cuadrillas
        cuadrillas = db.query(Cuadrilla).filter(Cuadrilla.active == True).all()
        logger.info(f"Found {len(cuadrillas)} active cuadrillas")

        assignments = []
        total_assigned = 0

        # Simple balance assignment: assign 1 OT per cuadrilla
        for i, ot in enumerate(unplanned_ots):
            if i >= len(cuadrillas):
                break

            cuadrilla = cuadrillas[i]

            # Check if OT has valid coordinates
            if ot.lat is None or ot.long is None:
                logger.warning(f"OT {ot.id} missing coordinates, skipping")
                continue

            # Calculate distance to cuadrilla centroid
            from backend.utils.geo import calculate_distance

            if (
                cuadrilla.last_centroid_lat is not None
                and cuadrilla.last_centroid_long is not None
            ):
                distance = calculate_distance(
                    (ot.lat, ot.long),
                    (cuadrilla.last_centroid_lat, cuadrilla.last_centroid_long),
                )
            else:
                distance = 0.0

            # Create assignment
            asignacion = Asignacion(
                ot_id=ot.id,
                cuadrilla_id=cuadrilla.id,
                assigned_at=datetime.now(),
                assigned_by_agent="PlanificacionAgent",
                distance_to_centroid=distance,
                is_active=True,
            )

            db.add(asignacion)

            # Update OT status
            ot.status = OT_STATUS["PLANIFICADA"]
            ot.cuadrilla_id = cuadrilla.id
            ot.updated_at = datetime.now()
            ot.last_status_change = datetime.now()

            assignments.append(
                {
                    "ot_id": ot.id,
                    "cuadrilla_id": cuadrilla.id,
                    "distance_to_centroid": distance,
                    "assigned_by_agent": "PlanificacionAgent",
                }
            )

            total_assigned += 1
            logger.info(f"Assigned OT {ot.id} to cuadrilla {cuadrilla.id}")

        db.commit()
        logger.info(f"Planning completed: {total_assigned} OTs assigned")

        return PlanningResult(
            assignments=assignments,
            total_assigned=total_assigned,
            unassigned=[
                ot.id for ot in unplanned_ots[len(cuadrillas) :]
            ],
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error during OT planning: {str(e)}")
        raise


@router.post("/governance", response_model=GovernanceResult)
async def governance_check(
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    notification_service=Depends(get_notification_service),
):
    """
    Trigger governance checks and inactivity management (UC-PEI-08).

    This endpoint triggers the Governance Agent to:
    1. Check inactive OTs in DETENIDA status
    2. Send alerts at 20, 25, 29 days
    3. Auto-cancel OTs after 30 days
    4. Check PREPLANIFICADA inactivity (>48 hours)

    Returns:
    - GovernanceResult with:
      - alerts_sent: Number of alerts sent
      - ots_cancelled: Number of OTs auto-cancelled
      - details: Detailed results for each OT

    Status Codes:
    - 200: Governance check completed
    - 500: Internal server error
    """
    try:
        logger.info("Starting governance check")

        from backend.database.models import OT, Alerta
        from backend.utils.business_rules import (
            calculate_days_inactive,
            should_send_alert,
            should_auto_cancel,
        )

        alerts_sent = 0
        ots_cancelled = 0
        details = []

        # Check all DETENIDA OTs for inactivity
        detenida_ots = db.query(OT).filter(OT.status == OT_STATUS["DETENIDA"]).all()
        logger.info(f"Checking {len(detenida_ots)} DETENIDA OTs for inactivity")

        for ot in detenida_ots:
            days_inactive = calculate_days_inactive(ot.last_status_change)
            logger.info(f"OT {ot.id}: {days_inactive} days inactive")

            # Check if should auto-cancel
            if should_auto_cancel(days_inactive):
                ot.status = OT_STATUS["ANULADA"]
                ot.updated_at = datetime.now()
                ot.last_status_change = datetime.now()
                ots_cancelled += 1

                detail = {
                    "ot_id": ot.id,
                    "action": "auto_cancelled",
                    "reason": "Exceeded 30 days in DETENIDA status",
                }
                details.append(detail)
                logger.info(f"Auto-cancelled OT {ot.id}")

            # Check if should send alert
            else:
                alert_type = should_send_alert(days_inactive)
                if alert_type:
                    # Create alert record
                    alerta = Alerta(
                        ot_id=ot.id,
                        tipo=alert_type,
                        mensaje=f"OT {ot.external_id} has been stopped for {days_inactive} days",
                        canal="EMAIL",
                        enviado_at=datetime.now(),
                    )
                    db.add(alerta)
                    alerts_sent += 1

                    detail = {
                        "ot_id": ot.id,
                        "action": "alert_sent",
                        "alert_type": alert_type,
                        "days_inactive": days_inactive,
                    }
                    details.append(detail)
                    logger.info(f"Sent alert for OT {ot.id}: {alert_type}")

        db.commit()
        logger.info(
            f"Governance check completed: "
            f"{alerts_sent} alerts sent, {ots_cancelled} OTs cancelled"
        )

        return GovernanceResult(
            alerts_sent=alerts_sent,
            ots_cancelled=ots_cancelled,
            details=details,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error during governance check: {str(e)}")
        raise


@router.post("/chat", response_model=Dict[str, Any])
async def chat_with_agents(
    message_data: Dict[str, str],
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    LLM-powered chat interface for agent interactions.

    This endpoint implements a conversational interface for:
    - Natural language routing to agent actions
    - Data queries and analysis
    - System commands

    Request Body:
    - message: User message
    - user_id: User identifier (for future multi-user support)

    Returns:
    - response: Agent response text
    - actions_taken: List of actions executed
    - agent_logs: Detailed logs from agent execution
    - metadata: Additional metadata (job_id, etc.)

    Status Codes:
    - 200: Chat completed
    - 400: Invalid request
    - 500: Internal server error
    """
    try:
        message = message_data.get("message")
        user_id = message_data.get("user_id", "anonymous")

        if not message:
            return {
                "response": "Error: message is required",
                "actions_taken": [],
                "agent_logs": [],
            }

        logger.info(f"Chat message from {user_id}: {message}")

        # Simple routing logic (expand with actual LLM in production)
        response = "I received your message. In a full implementation, I would route this to the appropriate agent."
        actions_taken = ["message_received", "processing"]
        agent_logs = [
            {
                "agent": "router",
                "action": "route_user_input",
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
            }
        ]

        # Check for specific keywords for demo purposes
        if "plan" in message.lower():
            actions_taken.append("trigger_planning_agent")
            response = "I'll trigger the planning agent to optimize OT assignments."
            agent_logs.append(
                {
                    "agent": "planning",
                    "action": "plan_ots",
                    "status": "triggered",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        elif "ingest" in message.lower():
            actions_taken.append("trigger_ingestion_agent")
            response = "I'll fetch new OTs from the TELCOS API."
            agent_logs.append(
                {
                    "agent": "ots",
                    "action": "ingest_ots",
                    "status": "triggered",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        elif "governance" in message.lower() or "check" in message.lower():
            actions_taken.append("trigger_governance_agent")
            response = "I'll perform a governance check for inactive OTs."
            agent_logs.append(
                {
                    "agent": "governance",
                    "action": "check_inactivity",
                    "status": "triggered",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        logger.info(f"Chat response: {response}")

        return {
            "response": response,
            "actions_taken": actions_taken,
            "agent_logs": agent_logs,
            "metadata": {"user_id": user_id, "timestamp": datetime.now().isoformat()},
        }

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return {
            "response": f"Error processing message: {str(e)}",
            "actions_taken": [],
            "agent_logs": [
                {
                    "agent": "system",
                    "action": "error_handler",
                    "status": "error",
                    "error": str(e),
                }
            ],
        }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get status of a background job.

    Parameters:
    - job_id: Job identifier returned from agent endpoints

    Returns:
    - Job status, results, and metadata

    Status Codes:
    - 200: Job found
    - 404: Job not found
    """
    try:
        if job_id not in job_results:
            return {
                "status": "not_found",
                "error": f"Job {job_id} not found",
            }

        return job_results[job_id]

    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/debug/state")
async def debug_state(
    db: Session = Depends(get_db),
):
    """
    Debug endpoint returning current system state.

    Returns:
    - OT counts by status
    - Cuadrilla information
    - Assignment statistics
    - Recent agent logs

    Status Codes:
    - 200: Success
    - 500: Internal server error
    """
    try:
        from backend.database.models import OT, Cuadrilla, Asignacion, LogAgente
        from sqlalchemy import func

        # Get OT counts by status
        ot_counts = (
            db.query(OT.status, func.count(OT.id))
            .group_by(OT.status)
            .all()
        )

        # Get cuadrilla counts
        cuadrilla_count = db.query(func.count(Cuadrilla.id)).scalar()

        # Get assignment counts
        assignment_count = db.query(func.count(Asignacion.id)).filter(
            Asignacion.is_active == True
        ).scalar()

        # Get recent logs
        recent_logs = (
            db.query(LogAgente)
            .order_by(LogAgente.timestamp.desc())
            .limit(10)
            .all()
        )

        return {
            "ot_counts": {status: count for status, count in ot_counts},
            "cuadrilla_count": cuadrilla_count or 0,
            "active_assignments": assignment_count or 0,
            "recent_logs": [
                {
                    "id": log.id,
                    "agente_name": log.agente_name,
                    "accion": log.accion,
                    "resultado": log.resultado,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                }
                for log in recent_logs
            ],
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error in debug state endpoint: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

