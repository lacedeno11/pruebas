import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.services.telcos_service import TelcosService
from backend.app.models.ot import OT, OTStatus, ProjectType
from backend.app.models.log_agente import LogAgente
from backend.app.core.database import get_db

logger = logging.getLogger(__name__)


class OTSAgent:
    """
    OTSAgent handles OT (Orden de Trabajo) ingestion and management.
    
    Responsibilities:
    - Fetch OTs from TELCOS system via TelcosService
    - Validate geographic coordinates
    - Persist OTs to database
    - Log all ingestion actions and errors
    """

    def __init__(self):
        """Initialize OTSAgent with TelcosService."""
        self.telcos_service = TelcosService()
        self.agent_name = "OTSAgent"

    async def ingest_ots(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch OTs from TELCOS system, validate, and persist to database.
        
        Process:
        1. Fetch OTs from TelcosService (which uses MOCK or PRODUCTION backend)
        2. Validate each OT:
           - Check if coordinates (lat/long) are present
           - Mark error_geo if coordinates are missing
           - Validate project_type is one of the enum values
        3. Check if OT already exists (by external_id)
           - If exists, update it
           - If not, create new OT
        4. Log all operations to logs_agentes table
        5. Return updated state with ingestion results
        
        Args:
            state: AgentState dictionary with optional input field
        
        Returns:
            Updated state with ingestion results, OT count, and errors
        """
        ingestion_results = {
            "total_fetched": 0,
            "created": 0,
            "updated": 0,
            "errors": 0,
            "geo_errors": 0,
            "messages": []
        }

        db = next(get_db())
        try:
            # Fetch OTs from TELCOS system
            logger.info("Starting OT ingestion from TELCOS system")
            telcos_ots = await self.telcos_service.get_ots()

            if not telcos_ots:
                message = "No OTs returned from TELCOS system"
                logger.warning(message)
                ingestion_results["messages"].append(message)
                
                # Log this action
                self._log_action(
                    db,
                    ot_id=None,
                    accion="fetch_ots",
                    resultado="NO_DATA",
                    raw_response=None
                )
                
                return {
                    **state,
                    "action": "INGEST_COMPLETE",
                    "result": ingestion_results,
                    "ots": []
                }

            ingestion_results["total_fetched"] = len(telcos_ots)
            logger.info(f"Fetched {len(telcos_ots)} OTs from TELCOS system")

            # Process each OT
            processed_ots = []
            for ot_data in telcos_ots:
                try:
                    ot_dict = self._process_ot(db, ot_data, ingestion_results)
                    processed_ots.append(ot_dict)
                except Exception as e:
                    error_msg = f"Error processing OT {ot_data.get('external_id', 'UNKNOWN')}: {str(e)}"
                    logger.error(error_msg)
                    ingestion_results["errors"] += 1
                    ingestion_results["messages"].append(error_msg)
                    
                    # Log the error
                    self._log_action(
                        db,
                        ot_id=ot_data.get('external_id'),
                        accion="process_ot",
                        resultado="ERROR",
                        raw_response=str(e)
                    )

            # Commit database changes
            try:
                db.commit()
                logger.info(
                    f"OT ingestion completed: {ingestion_results['created']} created, "
                    f"{ingestion_results['updated']} updated, {ingestion_results['errors']} errors"
                )
                ingestion_results["messages"].append(
                    f"Ingestion complete: {ingestion_results['created']} created, "
                    f"{ingestion_results['updated']} updated"
                )
            except Exception as e:
                db.rollback()
                error_msg = f"Database commit failed: {str(e)}"
                logger.error(error_msg)
                ingestion_results["errors"] += 1
                ingestion_results["messages"].append(error_msg)

            return {
                **state,
                "action": "INGEST_COMPLETE",
                "result": ingestion_results,
                "ots": processed_ots
            }

        except Exception as e:
            error_msg = f"Fatal error during OT ingestion: {str(e)}"
            logger.error(error_msg)
            ingestion_results["errors"] += 1
            ingestion_results["messages"].append(error_msg)
            
            # Log the fatal error
            self._log_action(
                db,
                ot_id=None,
                accion="ingest_ots",
                resultado="FATAL_ERROR",
                raw_response=str(e)
            )

            return {
                **state,
                "action": "INGEST_ERROR",
                "result": ingestion_results,
                "errors": [error_msg]
            }
        finally:
            db.close()

    def _process_ot(self, db: Session, ot_data: Dict[str, Any], results: Dict[str, int]) -> Dict[str, Any]:
        """
        Process a single OT: validate, create or update in database.
        
        Args:
            db: SQLAlchemy session
            ot_data: OT data from TELCOS
            results: Results dictionary to track statistics
        
        Returns:
            Processed OT dictionary
        
        Raises:
            ValueError: If OT data is invalid
        """
        # Validate required fields
        if "external_id" not in ot_data:
            raise ValueError("Missing required field: external_id")
        if "project_type" not in ot_data:
            raise ValueError("Missing required field: project_type")

        external_id = ot_data["external_id"]
        
        # Check if OT already exists
        existing_ot = db.query(OT).filter(OT.external_id == external_id).first()

        # Validate and process coordinates
        lat = ot_data.get("lat")
        long = ot_data.get("long")
        error_geo = lat is None or long is None

        if error_geo:
            results["geo_errors"] += 1
            logger.warning(f"OT {external_id} has missing geographic coordinates")

        # Validate project type
        try:
            project_type = ProjectType(ot_data["project_type"])
        except ValueError:
            raise ValueError(f"Invalid project_type: {ot_data['project_type']}")

        # Validate status if provided
        status = OTStatus.PREPLANIFICADA
        if "status" in ot_data:
            try:
                status = OTStatus(ot_data["status"])
            except ValueError:
                logger.warning(f"Invalid status {ot_data.get('status')}, using PREPLANIFICADA")

        if existing_ot:
            # Update existing OT
            existing_ot.status = status
            existing_ot.project_type = project_type
            existing_ot.cliente_id = ot_data.get("cliente_id", existing_ot.cliente_id)
            existing_ot.login_id = ot_data.get("login_id", existing_ot.login_id)
            existing_ot.lat = lat
            existing_ot.long = long
            existing_ot.error_geo = error_geo
            existing_ot.updated_at = datetime.utcnow()

            db.add(existing_ot)
            results["updated"] += 1
            
            logger.info(f"Updated OT {external_id}")
            
            # Log update action
            self._log_action(
                db,
                ot_id=external_id,
                accion="update_ot",
                resultado="SUCCESS",
                raw_response=str(ot_data)
            )

            return {
                "id": existing_ot.id,
                "external_id": existing_ot.external_id,
                "status": existing_ot.status.value,
                "project_type": existing_ot.project_type.value,
                "cliente_id": existing_ot.cliente_id,
                "login_id": existing_ot.login_id,
                "lat": existing_ot.lat,
                "long": existing_ot.long,
                "error_geo": existing_ot.error_geo,
                "created_at": existing_ot.created_at,
                "updated_at": existing_ot.updated_at
            }
        else:
            # Create new OT
            new_ot = OT(
                external_id=external_id,
                status=status,
                project_type=project_type,
                cliente_id=ot_data.get("cliente_id", ""),
                login_id=ot_data.get("login_id", ""),
                lat=lat,
                long=long,
                error_geo=error_geo,
                cuadrilla_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.add(new_ot)
            db.flush()  # Flush to get the ID
            results["created"] += 1

            logger.info(f"Created new OT {external_id} with ID {new_ot.id}")

            # Log creation action
            self._log_action(
                db,
                ot_id=external_id,
                accion="create_ot",
                resultado="SUCCESS",
                raw_response=str(ot_data)
            )

            return {
                "id": new_ot.id,
                "external_id": new_ot.external_id,
                "status": new_ot.status.value,
                "project_type": new_ot.project_type.value,
                "cliente_id": new_ot.cliente_id,
                "login_id": new_ot.login_id,
                "lat": new_ot.lat,
                "long": new_ot.long,
                "error_geo": new_ot.error_geo,
                "created_at": new_ot.created_at,
                "updated_at": new_ot.updated_at
            }

    def _log_action(
        self,
        db: Session,
        ot_id: str,
        accion: str,
        resultado: str,
        raw_response: str = None
    ) -> None:
        """
        Log an agent action to the logs_agentes table.
        
        Args:
            db: SQLAlchemy session
            ot_id: External OT ID (can be None for system-level actions)
            accion: Action performed
            resultado: Result of the action
            raw_response: Raw response from service or error message
        """
        try:
            log_entry = LogAgente(
                ot_id=None,  # We use external_id in the action, not DB ID
                agente_name=self.agent_name,
                accion=accion,
                resultado=resultado,
                raw_llm_response=raw_response,
                timestamp=datetime.utcnow()
            )
            db.add(log_entry)
            db.flush()
        except Exception as e:
            logger.error(f"Failed to log action: {str(e)}")

