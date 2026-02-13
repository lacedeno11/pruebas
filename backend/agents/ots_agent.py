"""OTS Agent for OT ingestion and validation (UC-PEI-01)"""

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from backend.database.models import OT, LogAgente, Alerta
from backend.services.telcos_service import TelcosService
from backend.models.proyecto import IngestionResult
from backend.agents.graph import PEIState
from backend.utils.constants import OT_STATUS

logger = logging.getLogger(__name__)


class OTSAgent:
    """
    OTS Agent for ingesting and validating Work Orders (Órdenes de Trabajo).

    This agent implements UC-PEI-01 (OT Ingestion) with the following responsibilities:
    1. Fetch OTs from TELCOS API via TelcosService
    2. Validate each OT (check coordinates are not null)
    3. Create OT records in database with status PREPLANIFICADA (if valid)
    4. Create ERROR_GEO alert records for invalid OTs
    5. Create audit log entries for all operations
    6. Return ingestion results to caller
    """

    def __init__(self, db_session: Session, telcos_service: TelcosService):
        """
        Initialize OTSAgent with database session and TELCOS service.

        Args:
            db_session: SQLAlchemy database session
            telcos_service: Service for fetching OTs from TELCOS API
        """
        self.db_session = db_session
        self.telcos_service = telcos_service

        logger.info("OTSAgent initialized")

    async def execute(self, state: PEIState) -> PEIState:
        """
        Execute OT ingestion pipeline (UC-PEI-01).

        This method orchestrates the complete OT ingestion process:
        1. Fetch OTs from TELCOS API
        2. Validate coordinates for each OT
        3. Create OT records or error alerts
        4. Create audit logs
        5. Update state with results

        Args:
            state: Current PEI state

        Returns:
            Updated state with IngestionResult

        Raises:
            Exception: If database or API errors occur (wrapped and logged)
        """
        try:
            logger.info("OTSAgent: Starting OT ingestion")

            # Fetch OTs from TELCOS API
            ots_data = await self.telcos_service.fetch_ots()
            logger.info(f"OTSAgent: Fetched {len(ots_data)} OTs from TELCOS API")

            # Initialize result tracking
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
                    if not self._validate_coordinates(ot_data):
                        result.errors += 1

                        # Create ERROR_GEO alert
                        error_detail = self._handle_invalid_ot(ot_data)
                        result.error_details.append(error_detail)

                        logger.warning(
                            f"OTSAgent: OT {ot_data.get('external_id')} "
                            "has invalid coordinates"
                        )
                        continue

                    # Check if OT already exists
                    external_id = ot_data.get("external_id")
                    existing_ot = (
                        self.db_session.query(OT)
                        .filter(OT.external_id == external_id)
                        .first()
                    )

                    if existing_ot:
                        logger.info(
                            f"OTSAgent: OT {external_id} already exists, skipping"
                        )
                        result.error_details.append(
                            {
                                "ot_id": external_id,
                                "error": "OT already exists",
                                "status": "WARNING",
                            }
                        )
                        continue

                    # Create new OT record
                    new_ot = self._create_ot_record(ot_data)
                    self.db_session.add(new_ot)
                    self.db_session.flush()  # Flush to get the OT ID

                    # Create success log entry
                    success_log = self._create_log_entry(
                        ot_id=new_ot.id,
                        ot_external_id=external_id,
                        resultado="SUCCESS",
                        metadata={"action": "created", "status": OT_STATUS["PREPLANIFICADA"]},
                    )
                    self.db_session.add(success_log)

                    result.inserted += 1
                    logger.info(f"OTSAgent: Created OT {external_id}")

                except Exception as ot_error:
                    result.errors += 1
                    error_detail = {
                        "ot_id": ot_data.get("external_id"),
                        "error": str(ot_error),
                        "status": "ERROR",
                    }
                    result.error_details.append(error_detail)

                    logger.error(
                        f"OTSAgent: Error processing OT {ot_data.get('external_id')}: "
                        f"{str(ot_error)}"
                    )

                    # Create error log entry
                    error_log = self._create_log_entry(
                        ot_id=None,
                        ot_external_id=ot_data.get("external_id"),
                        resultado="ERROR",
                        metadata={"error": str(ot_error)},
                    )
                    self.db_session.add(error_log)

            # Commit all changes
            self.db_session.commit()

            logger.info(
                f"OTSAgent: OT ingestion completed - "
                f"Total: {result.total}, Inserted: {result.inserted}, "
                f"Errors: {result.errors}"
            )

            # Update state with results
            state["validation_result"] = {
                "total": result.total,
                "inserted": result.inserted,
                "errors": result.errors,
            }

            # Add to agent logs
            state["agent_logs"].append(
                {
                    "agent": "ots",
                    "action": "ingest_ots",
                    "result": "success",
                    "total": result.total,
                    "inserted": result.inserted,
                    "errors": result.errors,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return state

        except Exception as e:
            logger.error(f"OTSAgent: Fatal error during OT ingestion: {str(e)}")

            self.db_session.rollback()

            # Set error state
            state["error"] = f"OTS agent ingestion error: {str(e)}"

            # Add error to agent logs
            state["agent_logs"].append(
                {
                    "agent": "ots",
                    "action": "ingest_ots",
                    "result": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return state

    def _validate_coordinates(self, ot_data: dict) -> bool:
        """
        Validate OT has valid coordinates.

        Valid coordinates must have both lat and long not null.

        Args:
            ot_data: OT data dictionary from API

        Returns:
            True if coordinates are valid, False otherwise
        """
        lat = ot_data.get("lat")
        long = ot_data.get("long")

        # Check if both lat and long are present and not None
        if lat is None or long is None:
            return False

        # Check valid ranges
        if not (-90 <= lat <= 90):
            return False

        if not (-180 <= long <= 180):
            return False

        return True

    def _handle_invalid_ot(self, ot_data: dict) -> dict:
        """
        Handle OT with invalid coordinates.

        Creates an Alerta record for PM notification and returns error detail.

        Args:
            ot_data: OT data with invalid coordinates

        Returns:
            Error detail dictionary
        """
        external_id = ot_data.get("external_id", "UNKNOWN")

        # Create alert for PM
        alerta = Alerta(
            ot_id=None,  # No OT record yet
            tipo="ERROR_GEO",
            mensaje=f"OT {external_id} has invalid coordinates (lat/long missing)",
            destinatario="PM",  # Project Manager
            canal="EMAIL",
            enviado_at=None,
            leido=False,
        )

        self.db_session.add(alerta)

        # Create error log entry
        error_log = self._create_log_entry(
            ot_id=None,
            ot_external_id=external_id,
            resultado="ERROR",
            metadata={
                "error": "Invalid coordinates",
                "lat": ot_data.get("lat"),
                "long": ot_data.get("long"),
            },
        )
        self.db_session.add(error_log)

        return {
            "ot_id": external_id,
            "error": "Invalid coordinates (lat/long missing or null)",
            "status": "ERROR_GEO",
        }

    def _create_ot_record(self, ot_data: dict) -> OT:
        """
        Create a new OT database record from API data.

        Args:
            ot_data: OT data from TELCOS API

        Returns:
            New OT SQLAlchemy model instance
        """
        now = datetime.now()

        return OT(
            external_id=ot_data.get("external_id"),
            cliente_id=ot_data.get("cliente_id"),
            login_id=ot_data.get("login_id"),
            status=ot_data.get("status", OT_STATUS["PREPLANIFICADA"]),
            project_type=ot_data.get("project_type"),
            lat=ot_data.get("lat"),
            long=ot_data.get("long"),
            created_at=now,
            updated_at=now,
            last_status_change=now,
            cuadrilla_id=None,  # Will be assigned during planning
            detalle_detencion=None,
        )

    def _create_log_entry(
        self,
        ot_id: Optional[int],
        ot_external_id: str,
        resultado: str,
        metadata: Optional[dict] = None,
    ) -> LogAgente:
        """
        Create an audit log entry for OT operation.

        Args:
            ot_id: Database OT ID (None if OT wasn't created)
            ot_external_id: External OT ID from API
            resultado: Operation result (SUCCESS, ERROR, WARNING)
            metadata: Additional metadata dictionary

        Returns:
            New LogAgente model instance
        """
        return LogAgente(
            ot_id=ot_id,
            agente_name="OTSAgent",
            accion="ingest_ot",
            resultado=resultado,
            raw_llm_response=None,
            metadata={
                "external_id": ot_external_id,
                "action": "ingestion",
                **(metadata or {}),
            },
        )

    async def validate_batch(self, ot_ids: list) -> dict:
        """
        Validate a batch of OT IDs for existence and integrity.

        Advanced method for validating already-ingested OTs.

        Args:
            ot_ids: List of OT database IDs

        Returns:
            Dictionary with validation results
        """
        try:
            logger.info(f"OTSAgent: Validating batch of {len(ot_ids)} OTs")

            valid_ots = []
            missing_coords = []

            for ot_id in ot_ids:
                ot = self.db_session.query(OT).filter(OT.id == ot_id).first()

                if not ot:
                    missing_coords.append(ot_id)
                    continue

                if self._validate_coordinates(
                    {"lat": ot.lat, "long": ot.long}
                ):
                    valid_ots.append(ot_id)
                else:
                    missing_coords.append(ot_id)

            logger.info(
                f"OTSAgent: Validation complete - "
                f"Valid: {len(valid_ots)}, Invalid: {len(missing_coords)}"
            )

            return {
                "valid_count": len(valid_ots),
                "invalid_count": len(missing_coords),
                "valid_ot_ids": valid_ots,
                "invalid_ot_ids": missing_coords,
            }

        except Exception as e:
            logger.error(f"OTSAgent: Error during batch validation: {str(e)}")
            return {
                "valid_count": 0,
                "invalid_count": len(ot_ids),
                "error": str(e),
            }

    async def get_ingestion_stats(self) -> dict:
        """
        Get statistics about ingested OTs.

        Returns:
            Dictionary with ingestion statistics
        """
        try:
            total_ots = self.db_session.query(OT).count()

            ots_with_coords = (
                self.db_session.query(OT)
                .filter((OT.lat is not None) & (OT.long is not None))
                .count()
            )

            ots_without_coords = total_ots - ots_with_coords

            logger.info(
                f"OTSAgent: Ingestion stats - Total: {total_ots}, "
                f"With coords: {ots_with_coords}, Without: {ots_without_coords}"
            )

            return {
                "total_ots": total_ots,
                "ots_with_coordinates": ots_with_coords,
                "ots_without_coordinates": ots_without_coords,
                "valid_percentage": (
                    (ots_with_coords / total_ots * 100) if total_ots > 0 else 0
                ),
            }

        except Exception as e:
            logger.error(f"OTSAgent: Error getting ingestion stats: {str(e)}")
            return {"error": str(e)}

