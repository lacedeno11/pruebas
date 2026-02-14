import json
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from app.agents.state import PEIState, set_action, set_current_agent, add_message
from app.config import get_settings
from app.models import LogAgente
from app.database import SessionLocal


class RouterAgent:
    """
    Router Agent for classifying user intents and routing to appropriate agents
    
    Responsible for:
    - Taking natural language user input
    - Using LLM to classify intent into specific actions
    - Routing to appropriate agent based on classified action
    - Logging routing decisions to audit trail
    """

    def __init__(self):
        """Initialize RouterAgent with OpenAI LLM and settings"""
        self.settings = get_settings()
        
        # Initialize ChatOpenAI LLM
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.1,  # Low temperature for consistent classification
            api_key=self.settings.OPENAI_API_KEY,
        )
        
        # Create prompt template for intent classification
        self.prompt_template = self.create_prompt()

    def create_prompt(self) -> PromptTemplate:
        """
        Create the prompt template for intent classification
        
        Returns:
            PromptTemplate configured for routing decisions
        """
        prompt_text = """You are a router agent in the PEI (Plataforma de Ejecución de Instalaciones) platform.
Your task is to classify the user's intent and extract relevant parameters.

Classify the user intent into one of these actions:
- 'sync_ots': Download or sync new work orders (OTs) from external sources
- 'plan_assignment': Assign OTs to crews (cuadrillas) using the planning algorithm
- 'check_governance': Review governance rules, alerts, and auto-cancellations
- 'send_notification': Send communications to stakeholders (Telegram, Email)
- 'query_status': Query the current state of OTs, crews, or system

IMPORTANT: You must respond with valid JSON only, no additional text.

User Input: {user_input}

Response format:
{{
    "action": "sync_ots|plan_assignment|check_governance|send_notification|query_status",
    "confidence": 0.0-1.0,
    "parameters": {{
        "ot_ids": [optional array of OT IDs if applicable],
        "force_balance": true/false if action is plan_assignment,
        "query_type": optional string for query_status (e.g., "pending_ots", "crew_status")
    }},
    "reasoning": "brief explanation of why this action was chosen"
}}"""
        
        return PromptTemplate(
            input_variables=["user_input"],
            template=prompt_text,
        )

    def classify_input(self, state: PEIState) -> PEIState:
        """
        Classify user input intent and route to appropriate agent
        
        Args:
            state: Current PEIState from LangGraph
        
        Returns:
            Updated PEIState with classified action and routing decision
        """
        user_input = state.get("user_input", "")
        db_session = state.get("db_session")
        
        if not user_input:
            # No user input provided
            state = set_action(state, "query_status")
            state = set_current_agent(state, "router")
            state = add_message(state, "agent", "No user input provided. Defaulting to query_status.")
            return state
        
        try:
            # Use LLM to classify intent
            prompt = self.prompt_template.format(user_input=user_input)
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()
            
            # Parse JSON response
            classification = json.loads(response_text)
            
            # Extract action and parameters
            action = classification.get("action", "query_status").lower()
            confidence = classification.get("confidence", 0.5)
            parameters = classification.get("parameters", {})
            reasoning = classification.get("reasoning", "")
            
            # Validate action is one of allowed values
            allowed_actions = [
                "sync_ots",
                "plan_assignment",
                "check_governance",
                "send_notification",
                "query_status",
            ]
            
            if action not in allowed_actions:
                action = "query_status"  # Default fallback
            
            # Update state with classification results
            state = set_action(state, action)
            state = set_current_agent(state, "router")
            
            # Extract OT IDs if provided in parameters
            if "ot_ids" in parameters and parameters["ot_ids"]:
                state["ot_ids"] = parameters["ot_ids"]
            
            # Set force_balance flag if planning
            if action == "plan_assignment" and "force_balance" in parameters:
                state["force_balance"] = parameters["force_balance"]
            
            # Add agent response message
            response_msg = f"Classified intent as '{action}' with confidence {confidence:.2f}. {reasoning}"
            state = add_message(state, "agent", response_msg)
            
            # Log routing decision
            self._log_routing_decision(
                db_session,
                user_input=user_input,
                classified_action=action,
                confidence=confidence,
                reasoning=reasoning,
            )
            
            return state
            
        except json.JSONDecodeError:
            # JSON parsing failed - log error and default to query_status
            state = set_action(state, "query_status")
            state = set_current_agent(state, "router")
            error_msg = f"Failed to parse LLM response as JSON. Defaulting to query_status."
            state = add_message(state, "agent", error_msg)
            
            self._log_routing_decision(
                db_session,
                user_input=user_input,
                classified_action="query_status",
                confidence=0.0,
                reasoning="JSON parse error - defaulted to query_status",
            )
            
            return state
            
        except Exception as e:
            # Unexpected error - log and default to query_status
            state = set_action(state, "query_status")
            state = set_current_agent(state, "router")
            error_msg = f"Error during intent classification: {str(e)}. Defaulting to query_status."
            state = add_message(state, "agent", error_msg)
            
            self._log_routing_decision(
                db_session,
                user_input=user_input,
                classified_action="query_status",
                confidence=0.0,
                reasoning=f"Exception: {str(e)}",
            )
            
            return state

    def _log_routing_decision(
        self,
        db_session: Optional[Session],
        user_input: str,
        classified_action: str,
        confidence: float,
        reasoning: str,
    ) -> None:
        """
        Log routing decision to LogAgente table for audit trail
        
        Args:
            db_session: SQLAlchemy session (optional)
            user_input: Original user input
            classified_action: Classified action
            confidence: Confidence score of classification
            reasoning: Reasoning for the classification
        """
        # If no session provided, create one temporarily
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            log_entry = LogAgente(
                agente_name="RouterAgent",
                accion="classify_input",
                resultado=classified_action,
                raw_llm_response=json.dumps({
                    "user_input": user_input,
                    "classified_action": classified_action,
                    "confidence": confidence,
                    "reasoning": reasoning,
                }),
            )
            db_session.add(log_entry)
            db_session.commit()
        except Exception as e:
            # Log error but don't raise - routing decision should proceed
            print(f"Error logging routing decision: {str(e)}")
            db_session.rollback()
        finally:
            if should_close:
                db_session.close()

