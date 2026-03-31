"""OTSAgent for OT ingestion from TELCOS API."""

import logging
from datetime import datetime
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.state import AgentState
from backend.app.models.ot import OrdenTrabajo, OTStatus, ProjectType
from backend.app.services.telcos_api_client import TelcosApiClient
from backend.app.utils.geo_utils import validate_coordinates

logger = logging.getLogger(__name__)


class OTSAgent(BaseAgent):
    """Ingests OTs from TELCOS API and persists to database."""

    async def execute(self, state: AgentState) -> AgentState:
        """Sync OTs from TELCOS API."""
        try:
            logger.info("OTSAgent: Starting OT sync")
            
            # Get OTs from TELCOS API
            telcos_client = TelcosApiClient()
            telcos_ots = await telcos_client.get_ots()
            logger.info(f"OTSAgent: Fetched {len(telcos_ots)} OTs from TELCOS")
            
            created_ots = []
            errors = []
            
            # Process each OT
            for telcos_ot in telcos_ots:
                try:
                    # Check if OT already exists
                    existing = self.db_session.query(OrdenTrabajo).filter(
                        OrdenTrabajo.external_id == telcos_ot.external_id
                    ).first()
                    
                    if existing:
                        logger.debug(f"OT {telcos_ot.external_id} already exists, skipping")
                        continue
                    
                    # Validate coordinates
                    error_geo = False
                    if telcos_ot.lat is not None and telcos_ot.long is not None:
                        if not validate_coordinates(telcos_ot.lat, telcos_ot.long):
                            error_geo = True
                            logger.warning(f"Invalid coordinates for {telcos_ot.external_id}")
                    
                    # Create new OT
                    new_ot = OrdenTrabajo(
                        external_id=telcos_ot.external_id,
                        status=OTStatus.PREPLANIFICADA,
                        project_type=telcos_ot.project_type,
                        lat=telcos_ot.lat,
                        long=telcos_ot.long,
                        cliente_id=telcos_ot.cliente_id,
                        login_id=telcos_ot.login_id,
                        error_geo=error_geo,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    
                    self.db_session.add(new_ot)
                    created_ots.append(str(new_ot.id))
                    
                except Exception as e:
                    error_msg = f"Error processing OT {getattr(telcos_ot, 'external_id', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Commit changes
            self.db_session.commit()
            
            # Log action
            self.log_action(
                action="SYNC_OTS",
                resultado="success" if not errors else "partial_success",
                metadata={
                    "created_count": len(created_ots),
                    "error_count": len(errors),
                    "created_ot_ids": created_ots,
                }
            )
            
            logger.info(f"OTSAgent: Sync complete - {len(created_ots)} created, {len(errors)} errors")
            
            # Update state
            state["agent_history"].append(self.agent_name)
            state["result"] = {
                "created_ots": created_ots,
                "created_count": len(created_ots),
                "error_count": len(errors),
                "errors": errors,
            }
            state["should_continue"] = True
            
            return state
            
        except Exception as e:
            logger.error(f"OTSAgent error: {str(e)}", exc_info=True)
            self.db_session.rollback()
            return self._update_state(state, error=str(e), should_continue=False)

