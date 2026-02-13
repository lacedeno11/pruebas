"""
OTSAgent for PEI Platform agentic system.
Fetches OTs from TELCOS API and persists them to the database.
"""

from typing import Dict, List
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.agents.base_agent import BaseAgent
from backend.models import OT
from backend.models.log_agente import ActionResult
from backend.services.telcos_service import TelcosService
from backend.schemas import OTCreate


class OTSAgent(BaseAgent):
    """
    OTSAgent that fetches OTs from TELCOS API and persists to database.

    OTSAgent is responsible for:
    1. Fetching OT list from TELCOS API via TelcosService
    2. Validating each OT has required geographic coordinates (lat, long)
    3. Setting geo_error flag for OTs missing coordinates
    4. Persisting OTs to database (bulk insert/update)
    5. Logging execution results and any errors

    The agent handles both new OT registration and updates to existing OTs.
    Geographic validation is critical as OTs without coordinates cannot be
    assigned to cuadrillas in the Planificación Agent.

    Error Handling:
    - OTs with missing coordinates are marked with geo_error=True
    - OTs are still persisted to DB even with geo_error flag
    - Errors are logged but don't prevent other OTs from being processed
    """

    def __init__(self, llm: ChatOpenAI, db_session: Session):
        """
        Initialize OTSAgent.

        Args:
            llm: ChatOpenAI instance for LLM operations (unused in OTSAgent but required by BaseAgent)
            db_session: SQLAlchemy session for database operations
        """
        super().__init__(llm, db_session)
        self.agent_name = "OTSAgent"
        self.telcos_service = TelcosService()

    async def execute(self, state: Dict) -> Dict:
        """
        Fetch OTs from TELCOS and persist to database.

        Implements complete workflow:
        1. Fetch OTs from TELCOS API via TelcosService.fetch_ots()
        2. Validate coordinates for each OT
        3. Check for duplicates and update existing OTs
        4. Persist to database
        5. Log results

        Args:
            state: Graph state containing:
                - user_input (str): User request or description
                - event_type (str): Type of event
                - Other state fields passed through

        Returns:
            Updated state with:
            - action_result (str): Description of OTs fetched and any errors
            - agent_logs (list): Updated with OTSAgent execution logs
            - ot_data (dict): Data about the operation (counts, errors, etc.)
        """
        try:
            # Step 1: Fetch OTs from TELCOS API
            ots_from_telcos = await self.telcos_service.fetch_ots()

            if not ots_from_telcos:
                action_result = "No OTs found from TELCOS API"
                self._log_action(
                    agente_name="OTSAgent",
                    accion="fetch_ots_from_telcos",
                    resultado=ActionResult.SUCCESS,
                    metadata={"ots_fetched": 0},
                )
                return {
                    **state,
                    "action_result": action_result,
                    "ot_data": {"ots_fetched": 0, "ots_with_errors": 0},
                }

            # Step 2: Process and persist OTs
            ots_registered = 0
            ots_with_geo_errors = 0
            ots_with_errors = []

            for ot_data in ots_from_telcos:
                try:
                    # Check for missing coordinates
                    has_geo_error = (
                        ot_data.get("lat") is None or ot_data.get("long") is None
                    )

                    if has_geo_error:
                        ots_with_geo_errors += 1

                    # Check if OT already exists by external_id
                    existing_ot = self.db_session.query(OT).filter(
                        OT.external_id == ot_data.get("external_id")
                    ).first()

                    if existing_ot:
                        # Update existing OT
                        existing_ot.status = ot_data.get("status", existing_ot.status)
                        existing_ot.project_type = ot_data.get(
                            "project_type", existing_ot.project_type
                        )
                        existing_ot.lat = ot_data.get("lat", existing_ot.lat)
                        existing_ot.long = ot_data.get("long", existing_ot.long)
                        existing_ot.geo_error = has_geo_error
                        if ot_data.get("detencion_motivo"):
                            existing_ot.detencion_motivo = ot_data.get(
                                "detencion_motivo"
                            )
                    else:
                        # Create new OT
                        new_ot = OT(
                            external_id=ot_data.get("external_id"),
                            cliente_id=ot_data.get("cliente_id"),
                            login_id=ot_data.get("login_id"),
                            status=ot_data.get("status", "PREPLANIFICADA"),
                            project_type=ot_data.get("project_type", "PRIVADO"),
                            lat=ot_data.get("lat"),
                            long=ot_data.get("long"),
                            geo_error=has_geo_error,
                            detencion_motivo=ot_data.get("detencion_motivo"),
                        )
                        self.db_session.add(new_ot)

                    ots_registered += 1

                    # Log warning if OT has geo error
                    if has_geo_error:
                        self._log_action(
                            agente_name="OTSAgent",
                            accion="ot_validation",
                            resultado=ActionResult.SUCCESS,
                            metadata={
                                "external_id": ot_data.get("external_id"),
                                "warning": "Missing geographic coordinates",
                            },
                        )

                except Exception as e:
                    # Log error but continue processing other OTs
                    ots_with_errors.append({
                        "external_id": ot_data.get("external_id"),
                        "error": str(e),
                    })
                    self._log_action(
                        agente_name="OTSAgent",
                        accion="ot_processing_error",
                        resultado=ActionResult.FAILURE,
                        metadata={
                            "external_id": ot_data.get("external_id"),
                            "error": str(e),
                        },
                    )

            # Step 3: Commit all changes to database
            try:
                self.db_session.commit()
            except Exception as e:
                self.db_session.rollback()
                action_result = f"Database commit failed: {str(e)}"
                self._log_action(
                    agente_name="OTSAgent",
                    accion="database_commit",
                    resultado=ActionResult.FAILURE,
                    metadata={"error": str(e)},
                )
                return {
                    **state,
                    "action_result": action_result,
                    "error_message": str(e),
                    "ot_data": {
                        "ots_fetched": len(ots_from_telcos),
                        "ots_registered": 0,
                        "ots_with_errors": ots_with_geo_errors,
                    },
                }

            # Step 4: Log overall success
            action_result = (
                f"Successfully registered {ots_registered} OTs from TELCOS. "
                f"{ots_with_geo_errors} OTs have missing coordinates."
            )

            if ots_with_errors:
                action_result += f" {len(ots_with_errors)} OTs failed to process."

            self._log_action(
                agente_name="OTSAgent",
                accion="fetch_and_persist_ots",
                resultado=ActionResult.SUCCESS,
                metadata={
                    "ots_fetched": len(ots_from_telcos),
                    "ots_registered": ots_registered,
                    "ots_with_geo_errors": ots_with_geo_errors,
                    "ots_with_errors": len(ots_with_errors),
                },
            )

            # Return updated state
            return {
                **state,
                "action_result": action_result,
                "ot_data": {
                    "ots_fetched": len(ots_from_telcos),
                    "ots_registered": ots_registered,
                    "ots_with_errors": ots_with_geo_errors,
                    "failed_ots": ots_with_errors,
                },
            }

        except Exception as e:
            # Handle unexpected errors
            action_result = f"OTSAgent failed: {str(e)}"
            self._log_action(
                agente_name="OTSAgent",
                accion="execute",
                resultado=ActionResult.FAILURE,
                metadata={"error": str(e)},
            )
            return {
                **state,
                "action_result": action_result,
                "error_message": str(e),
                "ot_data": {"ots_fetched": 0, "ots_registered": 0, "ots_with_errors": 0},
            }

