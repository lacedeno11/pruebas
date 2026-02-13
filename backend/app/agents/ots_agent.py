import json
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from langchain_openai import ChatOpenAI

from app.agents.state import PEIState, add_message, add_error
from app.config import get_settings
from app.models import OT, LogAgente
from app.services import MockApiService
from app.utils.geo import validate_ecuador_bounds
from app.database import SessionLocal


class OTSAgent:
    """
    OTS (Orden de Trabajo Sistema) Agent for OT ingestion and validation
    
    Responsible for:
    - Retrieving OTs from mock or external APIs
    - Validating OT data (required fields, geographic bounds)
    - Persisting OTs to database
    - Marking OTs with geo_error flag if coordinates are invalid
    - Logging all OT processing decisions
    """

    def __init__(self):
        """Initialize OTSAgent with settings and services"""
        self.settings = get_settings()
        self.mock_service = MockApiService()
        
        # Initialize ChatOpenAI LLM for coordinate validation
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.1,
            api_key=self.settings.OPENAI_API_KEY,
        )

    def process_ots(self, state: PEIState) -> PEIState:
        """
        Process OTs from API source: fetch, validate, and persist to database
        
        Args:
            state: Current PEIState from LangGraph
        
        Returns:
            Updated PEIState with processing results and validation_result
        """
        db_session = state.get("db_session")
        
        # If no session provided, create one temporarily
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            # Retrieve OTs from configured source
            if self.settings.SYSTEM_MODE == "MOCK":
                # Use mock service for development/testing
                import asyncio
                ots_data = asyncio.run(self.mock_service.get_ots())
            else:
                # In production, would call actual external API
                ots_data = []
            
            # Process each OT
            created_count = 0
            updated_count = 0
            geo_error_count = 0
            validation_errors = []
            created_ot_ids = []
            
            for ot_data in ots_data:
                try:
                    # Validate required fields
                    required_fields = ["external_id", "status", "project_type", "cliente_id", "login_id"]
                    missing_fields = [field for field in required_fields if not ot_data.get(field)]
                    
                    if missing_fields:
                        validation_errors.append(
                            f"OT {ot_data.get('external_id', 'UNKNOWN')}: Missing fields {missing_fields}"
                        )
                        state = add_error(state, validation_errors[-1])
                        continue
                    
                    # Validate geo coordinates
                    geo_error = False
                    lat = ot_data.get("lat")
                    long = ot_data.get("long")
                    
                    if lat is None or long is None:
                        geo_error = True
                        geo_error_count += 1
                    else:
                        # Validate Ecuador bounds
                        if not self.validate_coordinates(lat, long):
                            geo_error = True
                            geo_error_count += 1
                    
                    # Check if OT already exists
                    existing_ot = db_session.query(OT).filter(
                        OT.external_id == ot_data["external_id"]
                    ).first()
                    
                    if existing_ot:
                        # Update existing OT
                        existing_ot.status = ot_data.get("status", existing_ot.status)
                        existing_ot.project_type = ot_data.get("project_type", existing_ot.project_type)
                        existing_ot.lat = lat
                        existing_ot.long = long
                        existing_ot.geo_error = geo_error
                        existing_ot.updated_at = datetime.utcnow()
                        
                        db_session.commit()
                        updated_count += 1
                        ot_id = existing_ot.id
                    else:
                        # Create new OT
                        new_ot = OT(
                            external_id=ot_data["external_id"],
                            status=ot_data["status"],
                            project_type=ot_data["project_type"],
                            lat=lat,
                            long=long,
                            cliente_id=ot_data["cliente_id"],
                            login_id=ot_data["login_id"],
                            geo_error=geo_error,
                            detention_reason=ot_data.get("detention_reason"),
                            created_at=datetime.utcnow(),
                        )
                        db_session.add(new_ot)
                        db_session.commit()
                        db_session.refresh(new_ot)
                        
                        created_count += 1
                        ot_id = new_ot.id
                    
                    created_ot_ids.append(ot_id)
                    
                    # Log OT processing
                    self._log_ot_processing(
                        db_session,
                        ot_id=ot_id,
                        external_id=ot_data["external_id"],
                        geo_error=geo_error,
                        validation_passed=len(missing_fields) == 0,
                    )
                    
                except Exception as e:
                    validation_errors.append(
                        f"Error processing OT {ot_data.get('external_id', 'UNKNOWN')}: {str(e)}"
                    )
                    state = add_error(state, validation_errors[-1])
                    continue
            
            # Update state with results
            state["ot_ids"] = created_ot_ids
            state["validation_result"] = {
                "created_count": created_count,
                "updated_count": updated_count,
                "geo_error_count": geo_error_count,
                "validation_errors": validation_errors,
                "total_processed": created_count + updated_count,
            }
            
            # Add summary message
            summary_msg = (
                f"OTS Agent: Processed {created_count + updated_count} OTs "
                f"({created_count} created, {updated_count} updated). "
                f"{geo_error_count} OTs flagged with geo_error."
            )
            state = add_message(state, "agent", summary_msg)
            
            return state
            
        except Exception as e:
            # Log critical error
            error_msg = f"Critical error in OTS Agent: {str(e)}"
            state = add_error(state, error_msg)
            state = add_message(state, "agent", error_msg)
            state["validation_result"] = {
                "created_count": 0,
                "updated_count": 0,
                "geo_error_count": 0,
                "validation_errors": [error_msg],
                "total_processed": 0,
            }
            
            self._log_ot_processing(
                db_session,
                ot_id=None,
                external_id="ERROR",
                geo_error=False,
                validation_passed=False,
                error_message=error_msg,
            )
            
            return state
            
        finally:
            if should_close:
                db_session.close()

    def validate_coordinates(self, lat: float, long: float) -> bool:
        """
        Validate that coordinates are within Ecuador geographic bounds
        Uses Ecuador bounds: lat -5 to 2, long -92 to -75
        
        Args:
            lat: Latitude coordinate
            long: Longitude coordinate
        
        Returns:
            True if coordinates are valid, False otherwise
        """
        # Use utility function from geo module
        return validate_ecuador_bounds(lat, long)

    def _log_ot_processing(
        self,
        db_session: Optional[Session],
        ot_id: Optional[int],
        external_id: str,
        geo_error: bool,
        validation_passed: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log OT processing decision to LogAgente table for audit trail
        
        Args:
            db_session: SQLAlchemy session (optional)
            ot_id: OT database ID
            external_id: OT external identifier
            geo_error: Whether OT has geo error
            validation_passed: Whether validation passed
            error_message: Optional error message
        """
        # If no session provided, create one temporarily
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            log_entry = LogAgente(
                ot_id=ot_id,
                agente_name="OTSAgent",
                accion="process_ots",
                resultado="VALIDADO" if validation_passed else "ERROR",
                raw_llm_response=json.dumps({
                    "external_id": external_id,
                    "geo_error": geo_error,
                    "validation_passed": validation_passed,
                    "error_message": error_message,
                }),
            )
            db_session.add(log_entry)
            db_session.commit()
        except Exception as e:
            # Log error but don't raise - OT processing should proceed
            print(f"Error logging OT processing: {str(e)}")
            db_session.rollback()
        finally:
            if should_close:
                db_session.close()

