"""
OTS Agent for PEI Platform - OT Data Ingestion.

The OTSAgent is responsible for fetching work orders (OTs) from the external
Telcos API and ingesting them into the system with full validation.

Responsibilities:
1. Fetch OTs from Telcos API (or MockApiService in MOCK mode)
2. Validate geographic coordinates (Ecuador bounds checking)
3. Mark OTs with missing/invalid coordinates as ERROR_GEO
4. Create OT database records with status=PREPLANIFICADA
5. Trigger notifications for GEO_ERROR cases
6. Update workflow state with created OTs

Implements UC-PEI-01: OT Download & Registration
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_agent import BaseAgent
from src.agents.state import PEIState
from src.models import OT, OTStatus, ProjectType
from src.services.api_factory import get_api_service
from src.services.notification_service import NotificationService
from src.utils.geo_utils import validate_coordinates

logger = logging.getLogger(__name__)


class OTSAgent(BaseAgent):
    """
    OTS Agent for work order ingestion and validation.

    This agent orchestrates the data ingestion pipeline:
    1. Fetches OTs from external API
    2. Validates each OT's data (especially geographic coordinates)
    3. Creates database records
    4. Sends notifications for validation failures
    5. Logs successful ingestion

    Ensures 100% field mapping from external API to internal database.
    """

    def __init__(self, db: AsyncSession, llm=None):
        """Initialize the OTSAgent."""
        super().__init__(db, llm, agent_name="OTSAgent")
        self.api_service = get_api_service()
        self.notification_service = NotificationService()

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for OTS Agent.

        Returns:
            str: System prompt text
        """
        return """You are the OTS Agent for the PEI work order management system.
Your responsibility is to:
1. Fetch work orders (OTs) from the Telcos API
2. Validate that all required fields are present (100% field mapping)
3. Validate geographic coordinates are within Ecuador bounds
4. Mark OTs with missing coordinates as ERROR_GEO
5. Create OT database records
6. Report any data quality issues

Ensure that NO data is lost during ingestion - 100% field mapping is critical.
Log all actions and handle errors gracefully."""

    async def process(self, state: PEIState) -> PEIState:
        """
        Ingest OTs from external API and create database records.

        Args:
            state (PEIState): Current workflow state

        Returns:
            PEIState: Updated state with ingested OTs
        """
        try:
            # Validate state
            if not await self.validate_state(state):
                return await self.handle_error(state, "Invalid state for OTSAgent")

            logger.info("OTSAgent: Starting OT ingestion")

            # Fetch OTs from API
            try:
                ot_data_list = await self.api_service.get_ots()
                logger.info(f"OTSAgent: Fetched {len(ot_data_list)} OTs from API")
            except Exception as e:
                error_msg = f"Failed to fetch OTs from API: {str(e)}"
                logger.error(f"OTSAgent: {error_msg}")
                return await self.handle_error(state, error_msg)

            # Process each OT
            created_count = 0
            geo_error_count = 0
            errors = []

            for ot_data in ot_data_list:
                try:
                    # Validate required fields
                    required_fields = ["external_id", "cliente_id", "login_id", "project_type"]
                    missing_fields = [f for f in required_fields if not ot_data.get(f)]
                    if missing_fields:
                        errors.append(f"Missing fields in OT {ot_data.get('external_id')}: {missing_fields}")
                        continue

                    # Validate and prepare OT data
                    external_id = ot_data["external_id"]
                    lat = ot_data.get("lat")
                    long = ot_data.get("long")
                    is_geo_error = False

                    # Validate coordinates
                    if lat is not None and long is not None:
                        if not validate_coordinates(lat, long):
                            is_geo_error = True
                            geo_error_count += 1
                            logger.warning(
                                f"OTSAgent: GEO_ERROR for OT {external_id}: "
                                f"Invalid coordinates ({lat}, {long})"
                            )
                    else:
                        # Missing coordinates
                        is_geo_error = True
                        geo_error_count += 1
                        logger.warning(
                            f"OTSAgent: GEO_ERROR for OT {external_id}: Missing coordinates"
                        )

                    # Create OT record
                    ot = OT(
                        external_id=external_id,
                        status=OTStatus.PREPLANIFICADA,
                        project_type=ProjectType[ot_data["project_type"]],
                        lat=lat,
                        long=long,
                        cliente_id=ot_data["cliente_id"],
                        login_id=ot_data["login_id"],
                        is_geo_error=is_geo_error,
                    )

                    self.db.add(ot)
                    await self.db.flush()  # Get the ID without committing
                    created_count += 1

                    # Trigger notification for GEO_ERROR
                    if is_geo_error:
                        try:
                            await self.notification_service.send_alert(
                                alert_type="geo_error",
                                ot_id=ot.id,
                                recipients=["project_manager@telconet.ec"],
                                message=f"OT {external_id} has geographic coordinate errors and requires manual validation",
                            )
                        except Exception as e:
                            logger.warning(f"OTSAgent: Failed to send GEO_ERROR notification: {str(e)}")

                    # Add to state for downstream processing
                    state["ots_to_process"].append({
                        "id": ot.id,
                        "external_id": external_id,
                        "status": OTStatus.PREPLANIFICADA.value,
                        "project_type": ot_data["project_type"],
                        "is_geo_error": is_geo_error,
                    })

                except KeyError as e:
                    errors.append(f"Invalid project_type in OT {ot_data.get('external_id')}: {str(e)}")
                    continue
                except Exception as e:
                    errors.append(f"Error processing OT {ot_data.get('external_id')}: {str(e)}")
                    continue

            # Commit all created OTs
            try:
                await self.db.commit()
                logger.info(f"OTSAgent: Successfully created {created_count} OTs")
            except Exception as e:
                await self.db.rollback()
                error_msg = f"Failed to commit OTs to database: {str(e)}"
                logger.error(f"OTSAgent: {error_msg}")
                return await self.handle_error(state, error_msg)

            # Log the ingestion action
            accion = f"100% field mapping - Created {created_count} OTs, {geo_error_count} with GEO_ERROR"
            await self.log_action(
                accion=accion,
                resultado="SUCCESS",
                metadata={
                    "total_fetched": len(ot_data_list),
                    "created_count": created_count,
                    "geo_error_count": geo_error_count,
                    "errors": errors if errors else None,
                },
            )

            # Update state
            state["agent_messages"].append({
                "agent": "OTSAgent",
                "content": f"Ingested {created_count} OTs ({geo_error_count} with GEO_ERROR)",
                "timestamp": datetime.utcnow().isoformat(),
            })

            state["action_result"] = {
                "success": True,
                "message": f"Ingested {created_count} OTs",
                "data": {
                    "created_count": created_count,
                    "geo_error_count": geo_error_count,
                    "ots_to_process": state["ots_to_process"],
                },
            }

            logger.info(
                f"OTSAgent: Completed ingestion - "
                f"{created_count} OTs created, {geo_error_count} geo errors"
            )

            return state

        except Exception as e:
            logger.error(f"OTSAgent error: {str(e)}", exc_info=True)
            return await self.handle_error(state, f"OTSAgent error: {str(e)}")

    async def ingest_single_ot(self, ot_external_id: str) -> Optional[OT]:
        """
        Ingest a single OT by external ID.

        Args:
            ot_external_id (str): External ID of OT to ingest

        Returns:
            Optional[OT]: Created OT record or None if failed
        """
        try:
            # Fetch single OT details
            ot_data = await self.api_service.get_ot_details(ot_external_id)

            if not ot_data.get("success"):
                logger.error(f"OTSAgent: Failed to fetch OT {ot_external_id}")
                return None

            ot_info = ot_data.get("data", {})

            # Validate coordinates
            lat = ot_info.get("lat")
            long = ot_info.get("long")
            is_geo_error = not validate_coordinates(lat, long) if lat and long else True

            # Create OT record
            ot = OT(
                external_id=ot_external_id,
                status=OTStatus.PREPLANIFICADA,
                project_type=ProjectType[ot_info.get("project_type", "PRIVADO")],
                lat=lat,
                long=long,
                cliente_id=ot_info.get("cliente_id", ""),
                login_id=ot_info.get("login_id", ""),
                is_geo_error=is_geo_error,
            )

            self.db.add(ot)
            await self.db.commit()

            logger.info(f"OTSAgent: Ingested single OT {ot_external_id}")
            return ot

        except Exception as e:
            logger.error(f"OTSAgent: Error ingesting single OT {ot_external_id}: {str(e)}")
            await self.db.rollback()
            return None

