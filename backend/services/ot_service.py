"""
OT (Orden de Trabajo) Service for data access and business logic.
Handles OT creation, retrieval, status updates, and filtering.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from sqlalchemy.orm import Session
    from sqlalchemy import and_, or_
except ImportError:
    Session = None

from backend.services.geo_service import GeoService
from backend.services.notification_service import notification_service

# Configure logging
logger = logging.getLogger(__name__)


class OTService:
    """
    Service for OT (Orden de Trabajo) data access and business logic.
    
    Provides methods for:
    - Retrieving OTs with optional filtering
    - Creating new OTs with coordinate validation
    - Updating OT status with logging
    - Managing OT assignments to crews
    """

    @staticmethod
    def get_ots(
        db: Session,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """
        Retrieve OTs with optional filtering.
        
        Args:
            db: Database session
            filters: Optional dict with keys:
                - status: OT status (PREPLANIFICADA, PLANIFICADA, etc.)
                - project_type: Project type (PUBLICO, PRIVADO, TERCERIZADO)
                - geo_error: Boolean for OTs with missing coordinates
                - cuadrilla_id: Crew ID assignment filter
                
        Returns:
            List of OT objects matching filters
        """
        if not Session:
            logger.error("SQLAlchemy not available")
            return []

        try:
            # Import models dynamically to avoid circular imports
            from backend.database.models import OrdenTrabajo

            query = db.query(OrdenTrabajo)

            if filters:
                # Filter by status
                if "status" in filters and filters["status"]:
                    query = query.filter(OrdenTrabajo.status == filters["status"])

                # Filter by project type
                if "project_type" in filters and filters["project_type"]:
                    query = query.filter(
                        OrdenTrabajo.project_type == filters["project_type"]
                    )

                # Filter by geo_error
                if "geo_error" in filters:
                    query = query.filter(OrdenTrabajo.geo_error == filters["geo_error"])

                # Filter by cuadrilla_id
                if "cuadrilla_id" in filters and filters["cuadrilla_id"]:
                    query = query.filter(
                        OrdenTrabajo.cuadrilla_id == filters["cuadrilla_id"]
                    )

            # Order by created_at descending (most recent first)
            query = query.order_by(OrdenTrabajo.created_at.desc())

            return query.all()
        except Exception as e:
            logger.error(f"Error retrieving OTs: {e}")
            return []

    @staticmethod
    def get_ot_by_id(db: Session, ot_id: int) -> Optional[Any]:
        """
        Retrieve a single OT by ID.
        
        Args:
            db: Database session
            ot_id: OT internal ID
            
        Returns:
            OT object or None if not found
        """
        if not Session:
            logger.error("SQLAlchemy not available")
            return None

        try:
            from backend.database.models import OrdenTrabajo

            return db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
        except Exception as e:
            logger.error(f"Error retrieving OT {ot_id}: {e}")
            return None

    @staticmethod
    def get_ots_by_cuadrilla(db: Session, cuadrilla_id: int) -> List[Any]:
        """
        Retrieve all OTs assigned to a specific crew.
        
        Args:
            db: Database session
            cuadrilla_id: Crew ID
            
        Returns:
            List of OTs assigned to the crew
        """
        if not Session:
            return []

        try:
            from backend.database.models import OrdenTrabajo

            return db.query(OrdenTrabajo).filter(
                OrdenTrabajo.cuadrilla_id == cuadrilla_id
            ).all()
        except Exception as e:
            logger.error(f"Error retrieving OTs for cuadrilla {cuadrilla_id}: {e}")
            return []

    @staticmethod
    def get_unassigned_ots(db: Session) -> List[Any]:
        """
        Retrieve unassigned OTs in PREPLANIFICADA status.
        
        These are OTs ready for the planning algorithm to assign to crews.
        
        Args:
            db: Database session
            
        Returns:
            List of unassigned OTs
        """
        if not Session:
            return []

        try:
            from backend.database.models import OrdenTrabajo

            return db.query(OrdenTrabajo).filter(
                and_(
                    OrdenTrabajo.cuadrilla_id.is_(None),
                    OrdenTrabajo.status == "PREPLANIFICADA",
                )
            ).all()
        except Exception as e:
            logger.error(f"Error retrieving unassigned OTs: {e}")
            return []

    @staticmethod
    async def create_ot(db: Session, ot_data: Any) -> Dict[str, Any]:
        """
        Create a new OT with coordinate validation.
        
        Args:
            db: Database session
            ot_data: Pydantic OTCreate schema with OT data
            
        Returns:
            Created OT data or error dict
        """
        if not Session:
            return {
                "success": False,
                "error": "Database not available",
            }

        try:
            from backend.database.models import OrdenTrabajo

            # Validate coordinates
            geo_error = False
            if ot_data.lat is not None and ot_data.long is not None:
                if not GeoService.validate_coordinates(ot_data.lat, ot_data.long):
                    geo_error = True
                    logger.warning(
                        f"Invalid coordinates for OT {ot_data.external_id}: "
                        f"({ot_data.lat}, {ot_data.long})"
                    )
            else:
                geo_error = True
                logger.warning(
                    f"Missing coordinates for OT {ot_data.external_id}"
                )

            # Create OT record
            ot = OrdenTrabajo(
                external_id=ot_data.external_id,
                cliente_id=ot_data.cliente_id,
                orden_servicio_id=ot_data.orden_servicio_id,
                login_id=ot_data.login_id,
                status=ot_data.status or "PREPLANIFICADA",
                project_type=ot_data.project_type or "PRIVADO",
                lat=ot_data.lat,
                long=ot_data.long,
                geo_error=geo_error,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            db.add(ot)
            db.commit()
            db.refresh(ot)

            logger.info(f"OT created: {ot.external_id} (ID: {ot.id})")

            # Send notification if geo_error
            if geo_error:
                try:
                    # Get PM email from related data (placeholder)
                    pm_email = ot_data.pm_email if hasattr(ot_data, "pm_email") else None
                    if pm_email:
                        await notification_service.notify_pm_geo_error(
                            ot_id=ot.id,
                            ot_external_id=ot.external_id,
                            pm_email=pm_email,
                        )
                except Exception as e:
                    logger.error(f"Error sending geo_error notification: {e}")

            return {
                "success": True,
                "ot_id": ot.id,
                "external_id": ot.external_id,
                "geo_error": geo_error,
                "status": ot.status,
            }
        except Exception as e:
            logger.error(f"Error creating OT: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def update_ot_status(
        db: Session,
        ot_id: int,
        new_status: str,
        reason: Optional[str] = None,
        agent_name: str = "MANUAL_USER",
    ) -> Dict[str, Any]:
        """
        Update OT status and create log entry.
        
        Args:
            db: Database session
            ot_id: OT internal ID
            new_status: New OT status
            reason: Optional reason for status change (especially for DETENIDA)
            agent_name: Agent or user making the change
            
        Returns:
            Success/error response
        """
        if not Session:
            return {
                "success": False,
                "error": "Database not available",
            }

        try:
            from backend.database.models import OrdenTrabajo, LogAgente

            # Get OT
            ot = db.query(OrdenTrabajo).filter(OrdenTrabajo.id == ot_id).first()
            if not ot:
                return {
                    "success": False,
                    "error": f"OT {ot_id} not found",
                }

            # Store old status for logging
            old_status = ot.status

            # Update status
            ot.status = new_status
            ot.updated_at = datetime.now()

            # Create log entry
            log_entry = LogAgente(
                ot_id=ot_id,
                agente_name=agent_name,
                accion="UPDATE_STATUS",
                resultado=f"Status changed from {old_status} to {new_status}",
                raw_llm_response=reason or "",
                created_at=datetime.now(),
            )

            db.add(log_entry)
            db.commit()
            db.refresh(ot)

            logger.info(
                f"OT {ot.external_id} status updated: {old_status} -> {new_status}"
            )

            return {
                "success": True,
                "ot_id": ot.id,
                "external_id": ot.external_id,
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
                "updated_at": ot.updated_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Error updating OT status: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def get_ot_statistics(db: Session) -> Dict[str, Any]:
        """
        Get aggregated statistics about OTs.
        
        Args:
            db: Database session
            
        Returns:
            Statistics dict with counts by status, project_type, etc.
        """
        if not Session:
            return {}

        try:
            from backend.database.models import OrdenTrabajo
            from sqlalchemy import func

            total_ots = db.query(func.count(OrdenTrabajo.id)).scalar() or 0

            # Count by status
            status_counts = {}
            for status in [
                "PREPLANIFICADA",
                "PLANIFICADA",
                "ASIGNADO_TAREA",
                "DETENIDA",
                "ANULADA",
                "FINALIZADA",
            ]:
                count = (
                    db.query(func.count(OrdenTrabajo.id))
                    .filter(OrdenTrabajo.status == status)
                    .scalar()
                    or 0
                )
                status_counts[status] = count

            # Count by project type
            project_counts = {}
            for ptype in ["PUBLICO", "PRIVADO", "TERCERIZADO"]:
                count = (
                    db.query(func.count(OrdenTrabajo.id))
                    .filter(OrdenTrabajo.project_type == ptype)
                    .scalar()
                    or 0
                )
                project_counts[ptype] = count

            # Count geo errors
            geo_error_count = (
                db.query(func.count(OrdenTrabajo.id))
                .filter(OrdenTrabajo.geo_error == True)
                .scalar()
                or 0
            )

            # Count assigned OTs
            assigned_count = (
                db.query(func.count(OrdenTrabajo.id))
                .filter(OrdenTrabajo.cuadrilla_id.isnot(None))
                .scalar()
                or 0
            )

            return {
                "total_ots": total_ots,
                "by_status": status_counts,
                "by_project_type": project_counts,
                "geo_error_count": geo_error_count,
                "assigned_count": assigned_count,
                "unassigned_count": total_ots - assigned_count,
            }
        except Exception as e:
            logger.error(f"Error getting OT statistics: {e}")
            return {}

    @staticmethod
    def get_ot_logs(db: Session, ot_id: int) -> List[Any]:
        """
        Get all log entries for an OT.
        
        Args:
            db: Database session
            ot_id: OT ID
            
        Returns:
            List of LogAgente entries
        """
        if not Session:
            return []

        try:
            from backend.database.models import LogAgente

            return (
                db.query(LogAgente)
                .filter(LogAgente.ot_id == ot_id)
                .order_by(LogAgente.created_at.desc())
                .all()
            )
        except Exception as e:
            logger.error(f"Error retrieving OT logs: {e}")
            return []

    @staticmethod
    def bulk_create_ots(db: Session, ots_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple OTs in bulk (used by OTSAgent).
        
        Args:
            db: Database session
            ots_data: List of OT data dicts
            
        Returns:
            Summary of created OTs
        """
        if not Session:
            return {
                "success": False,
                "error": "Database not available",
            }

        created = 0
        failed = 0
        geo_errors = 0

        try:
            from backend.database.models import OrdenTrabajo

            for ot_data in ots_data:
                try:
                    # Validate coordinates
                    geo_error = False
                    if ot_data.get("lat") is not None and ot_data.get("long") is not None:
                        if not GeoService.validate_coordinates(
                            ot_data["lat"], ot_data["long"]
                        ):
                            geo_error = True
                    else:
                        geo_error = True

                    if geo_error:
                        geo_errors += 1

                    # Create OT record
                    ot = OrdenTrabajo(
                        external_id=ot_data.get("external_id"),
                        cliente_id=ot_data.get("cliente_id"),
                        orden_servicio_id=ot_data.get("orden_servicio_id"),
                        login_id=ot_data.get("login_id"),
                        status=ot_data.get("status", "PREPLANIFICADA"),
                        project_type=ot_data.get("project_type", "PRIVADO"),
                        lat=ot_data.get("lat"),
                        long=ot_data.get("long"),
                        geo_error=geo_error,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )

                    db.add(ot)
                    created += 1
                except Exception as e:
                    logger.error(f"Error creating OT from bulk data: {e}")
                    failed += 1

            db.commit()

            logger.info(
                f"Bulk OT creation: {created} created, {failed} failed, "
                f"{geo_errors} with geo_error"
            )

            return {
                "success": True,
                "created": created,
                "failed": failed,
                "geo_errors": geo_errors,
            }
        except Exception as e:
            logger.error(f"Error in bulk OT creation: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
            }


# Global instance
ot_service = OTService()

