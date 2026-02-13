"""
OTSAgent - Work Order ingestion and validation agent.
Fetches OTs from TELCOS/mock API, validates data, and persists to database.
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Settings
from backend.models import OrdenTrabajo, Cliente, Login, Proyecto
from backend.services import TelcosClient
from backend.utils import validate_ot_data, validate_coordinates
from backend.utils.logging_helper import log_agent_action

logger = logging.getLogger(__name__)


class OTSAgent:
    """
    OTSAgent - Ingests and validates work orders from TELCOS system.
    
    Responsibilities:
    1. Fetch OTs from TELCOS API (real or mock)
    2. Validate OT data (required fields, coordinates)
    3. Mark invalid coordinates as geo_error
    4. Create OrdenTrabajo database records
    5. Log all ingestion actions for audit trail
    6. Return ingestion summary
    """

    def __init__(
        self,
        llm: Optional[object] = None,
        telcos_client: Optional[TelcosClient] = None,
        db_session: Optional[AsyncSession] = None,
    ):
        """
        Initialize OTSAgent.

        Args:
            llm: OpenAI LLM instance (optional, for future enhancements)
            telcos_client: TelcosClient instance for fetching OTs
            db_session: AsyncSession for database operations
        """
        self.llm = llm
        self.telcos_client = telcos_client
        self.db_session = db_session

    async def ingest_ots(self) -> Dict[str, Any]:
        """
        Ingest OTs from TELCOS system.
        
        Process:
        1. Fetch OTs from telcos_client
        2. Validate each OT using validators
        3. Mark invalid coordinates as geo_error
        4. Create OrdenTrabajo records in database
        5. Log ingestion action
        6. Return summary
        
        Returns:
            Dictionary with ingestion summary:
            {
                "status": "success" | "partial" | "error",
                "total_fetched": int,
                "successful_ingestions": int,
                "failed_ingestions": int,
                "geo_errors": int,
                "errors": List[str],
                "summary": str
            }
        """
        logger.info("OTSAgent: Starting OT ingestion process")
        
        try:
            # Step 1: Fetch OTs from TELCOS (real or mock)
            if not self.telcos_client:
                logger.error("OTSAgent: TelcosClient not initialized")
                return {
                    "status": "error",
                    "total_fetched": 0,
                    "successful_ingestions": 0,
                    "failed_ingestions": 0,
                    "geo_errors": 0,
                    "errors": ["TelcosClient not initialized"],
                    "summary": "Failed: TelcosClient not configured",
                }

            ots_from_api = await self.telcos_client.fetch_ots()
            logger.info(f"OTSAgent: Fetched {len(ots_from_api)} OTs from TELCOS")

            # Initialize counters
            successful_ingestions = 0
            failed_ingestions = 0
            geo_errors = 0
            errors = []
            ingested_ot_ids = []

            # Step 2-5: Validate and persist each OT
            for ot_data in ots_from_api:
                try:
                    # Validate OT data (required fields, format)
                    is_valid, validation_error = await validate_ot_data(ot_data)
                    
                    if not is_valid:
                        logger.warning(f"OTSAgent: Validation failed for OT {ot_data.get('external_id')}: {validation_error}")
                        failed_ingestions += 1
                        errors.append(f"{ot_data.get('external_id', 'unknown')}: {validation_error}")
                        continue

                    # Check coordinates validity
                    lat = ot_data.get("lat")
                    long = ot_data.get("long")
                    geo_error = False

                    if lat is not None and long is not None:
                        is_coords_valid = await validate_coordinates(lat, long)
                        if not is_coords_valid:
                            logger.warning(
                                f"OTSAgent: Invalid coordinates for OT {ot_data['external_id']}: "
                                f"lat={lat}, long={long}"
                            )
                            geo_error = True
                            geo_errors += 1
                    else:
                        # Missing coordinates
                        logger.warning(
                            f"OTSAgent: Missing coordinates for OT {ot_data['external_id']}"
                        )
                        geo_error = True
                        geo_errors += 1

                    # Create OrdenTrabajo record
                    ot_record = OrdenTrabajo(
                        external_id=ot_data["external_id"],
                        cliente_id=UUID(ot_data["cliente_id"]) if isinstance(ot_data["cliente_id"], str) else ot_data["cliente_id"],
                        login_id=UUID(ot_data["login_id"]) if isinstance(ot_data["login_id"], str) else ot_data["login_id"],
                        proyecto_id=UUID(ot_data.get("proyecto_id")) if ot_data.get("proyecto_id") else None,
                        lat=lat,
                        long=long,
                        geo_error=geo_error,
                        status="PREPLANIFICADA",  # Initial status
                    )

                    if self.db_session:
                        self.db_session.add(ot_record)
                        ingested_ot_ids.append(str(ot_record.id))

                    successful_ingestions += 1
                    logger.info(f"OTSAgent: Successfully ingested OT {ot_data['external_id']}")

                except Exception as e:
                    logger.error(
                        f"OTSAgent: Error ingesting OT {ot_data.get('external_id', 'unknown')}: {str(e)}"
                    )
                    failed_ingestions += 1
                    errors.append(f"{ot_data.get('external_id', 'unknown')}: {str(e)}")

            # Commit database session if available
            if self.db_session:
                await self.db_session.commit()
                logger.info(f"OTSAgent: Committed {successful_ingestions} OT records to database")

            # Step 6: Log ingestion action
            summary = f"Ingested {successful_ingestions} OTs, {geo_errors} with coordinate errors, {failed_ingestions} failed"
            
            if self.db_session:
                await log_agent_action(
                    self.db_session,
                    agente_name="OTSAgent",
                    ot_id=None,  # Bulk operation, no single OT
                    accion="ingest_ots",
                    resultado=summary,
                    raw_llm_response={
                        "ingested_ids": ingested_ot_ids,
                        "successful": successful_ingestions,
                        "failed": failed_ingestions,
                    },
                )

            # Step 7: Return summary
            status = "success" if failed_ingestions == 0 else "partial" if successful_ingestions > 0 else "error"
            
            return {
                "status": status,
                "total_fetched": len(ots_from_api),
                "successful_ingestions": successful_ingestions,
                "failed_ingestions": failed_ingestions,
                "geo_errors": geo_errors,
                "errors": errors,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"OTSAgent: Critical error during ingestion: {str(e)}")
            return {
                "status": "error",
                "total_fetched": 0,
                "successful_ingestions": 0,
                "failed_ingestions": 0,
                "geo_errors": 0,
                "errors": [f"Critical error: {str(e)}"],
                "summary": f"Ingestion failed: {str(e)}",
            }


async def validate_ot_data(ot_dict: dict) -> tuple:
    """
    Validate OT data structure and required fields.
    
    Args:
        ot_dict: OT dictionary from TELCOS API
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    required_fields = ["external_id", "cliente_id", "login_id"]
    
    for field in required_fields:
        if field not in ot_dict or not ot_dict[field]:
            return False, f"Missing required field: {field}"
    
    return True, ""


async def validate_coordinates(lat: float, long: float) -> bool:
    """
    Validate coordinate ranges.
    
    Args:
        lat: Latitude (-90 to 90)
        long: Longitude (-180 to 180)
        
    Returns:
        True if coordinates valid, False otherwise
    """
    try:
        lat_f = float(lat)
        long_f = float(long)
        
        if not (-90 <= lat_f <= 90):
            return False
        if not (-180 <= long_f <= 180):
            return False
        
        return True
    except (TypeError, ValueError):
        return False

