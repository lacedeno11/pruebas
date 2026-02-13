"""Router Agent for intent classification and action routing"""

import logging
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from backend.database.models import LogAgente
from backend.agents.graph import PEIState

logger = logging.getLogger(__name__)


class RouterAgent:
    """
    Router Agent for classifying user intent and routing to appropriate agents.

    This agent acts as the entry point for user requests. It analyzes user input
    and determines which agent should handle the request (OTS Agent, Planning Agent,
    Governance Agent, Communication Agent, or queries).
    """

    def __init__(self, db_session: Session, llm_client: ChatOpenAI):
        """
        Initialize RouterAgent with database session and LLM client.

        Args:
            db_session: SQLAlchemy database session
            llm_client: LangChain ChatOpenAI client for LLM interactions
        """
        self.db_session = db_session
        self.llm_client = llm_client

        logger.info("RouterAgent initialized")

    async def execute(self, state: PEIState) -> PEIState:
        """
        Route user input to appropriate agent action.

        This method:
        1. Extracts user_input from state
        2. Calls LLM to classify intent
        3. Sets current_action based on classification
        4. Creates log entry in database
        5. Returns updated state

        Args:
            state: Current PEI state with user_input

        Returns:
            Updated state with current_action set

        Raises:
            Exception: If LLM call fails or database error occurs
        """
        try:
            user_input = state.get("user_input", "").strip()

            if not user_input:
                logger.warning("RouterAgent: Empty user input")
                state["current_action"] = "query"
                state["error"] = "No input provided"
                return state

            logger.info(f"RouterAgent: Processing user input: {user_input[:100]}")

            # Create prompt for intent classification
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a routing agent for the PEI (Plataforma de Ejecución de Instalaciones) platform.
Your task is to classify user intent and determine which agent should handle the request.

Available actions:
1. ingest_ots - For fetching and ingesting new work orders from TELCOS API
2. plan_ots - For planning and assigning work orders to teams
3. check_governance - For checking inactive work orders and auto-cancellation
4. send_notification - For sending notifications and alerts
5. query - For general queries and information requests

Analyze the user input and respond with ONLY the action name (one of the above).
Do not include any explanation or additional text.""",
                    ),
                    ("human", "User input: {user_input}"),
                ]
            )

            # Call LLM to classify intent
            chain = prompt | self.llm_client
            response = await chain.ainvoke({"user_input": user_input})

            # Extract action from response
            action = self._extract_action(response.content)

            logger.info(f"RouterAgent: Classified action: {action}")

            # Set current_action in state
            state["current_action"] = action

            # Create log entry in database
            log_entry = LogAgente(
                ot_id=None,  # Router agent is not specific to an OT
                agente_name="RouterAgent",
                accion="classify_intent",
                resultado="SUCCESS",
                raw_llm_response=response.content,
                metadata={
                    "user_input": user_input[:200],  # Truncate long inputs
                    "classified_action": action,
                },
            )

            self.db_session.add(log_entry)
            self.db_session.commit()

            logger.info(f"RouterAgent: Log entry created for action: {action}")

            # Add to state logs
            state["agent_logs"].append(
                {
                    "agent": "router",
                    "action": "classify_intent",
                    "result": "success",
                    "classified_action": action,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return state

        except Exception as e:
            logger.error(f"RouterAgent: Error during intent classification: {str(e)}")

            # Set error state
            state["error"] = f"Router agent error: {str(e)}"
            state["current_action"] = "query"  # Default to query on error

            # Create error log entry
            try:
                error_log = LogAgente(
                    ot_id=None,
                    agente_name="RouterAgent",
                    accion="classify_intent",
                    resultado="ERROR",
                    raw_llm_response=None,
                    metadata={"error": str(e)},
                )
                self.db_session.add(error_log)
                self.db_session.commit()
            except Exception as db_error:
                logger.error(f"RouterAgent: Failed to log error: {str(db_error)}")

            # Add to state logs
            state["agent_logs"].append(
                {
                    "agent": "router",
                    "action": "classify_intent",
                    "result": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return state

    def _extract_action(self, response_text: str) -> str:
        """
        Extract action name from LLM response.

        The LLM should return just the action name, but this method handles
        cases where extra text is included.

        Args:
            response_text: Raw response from LLM

        Returns:
            Cleaned action name or 'query' as fallback
        """
        # Valid actions
        valid_actions = ["ingest_ots", "plan_ots", "check_governance", "send_notification", "query"]

        # Clean response
        response_clean = response_text.strip().lower()

        # Check if response contains any valid action
        for action in valid_actions:
            if action in response_clean:
                return action

        # Default to query if no valid action found
        logger.warning(f"RouterAgent: Could not extract action from response: {response_text}")
        return "query"

    async def classify_with_confidence(
        self, user_input: str
    ) -> tuple[str, float]:
        """
        Classify user intent with confidence score.

        Advanced method for future use with confidence-based routing.

        Args:
            user_input: User input text

        Returns:
            Tuple of (action, confidence_score)
        """
        try:
            # Create prompt with confidence scoring
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """You are a routing agent for the PEI platform.
Classify user intent into one of these actions: ingest_ots, plan_ots, check_governance, send_notification, query.
Also provide a confidence score from 0 to 1.

Respond in format: ACTION: <action_name>, CONFIDENCE: <score>""",
                    ),
                    ("human", "User input: {user_input}"),
                ]
            )

            chain = prompt | self.llm_client
            response = await chain.ainvoke({"user_input": user_input})

            # Parse response
            response_text = response.content.lower()

            action = self._extract_action(response_text)

            # Extract confidence score
            confidence = 0.5  # Default
            if "confidence:" in response_text:
                try:
                    score_text = response_text.split("confidence:")[-1].strip()
                    confidence = float(score_text.split()[0])
                except (ValueError, IndexError):
                    pass

            logger.info(
                f"RouterAgent: Classified '{user_input[:50]}' as '{action}' "
                f"with confidence {confidence}"
            )

            return action, confidence

        except Exception as e:
            logger.error(f"RouterAgent: Error in classify_with_confidence: {str(e)}")
            return "query", 0.0

    def get_routing_rules(self) -> dict:
        """
        Get routing rules and action descriptions.

        Returns:
            Dictionary with action names as keys and descriptions as values
        """
        return {
            "ingest_ots": {
                "description": "Fetch and ingest new work orders from TELCOS API",
                "keywords": ["ingest", "fetch", "import", "new", "obtener", "traer"],
                "example_inputs": [
                    "Fetch new OTs from TELCOS",
                    "Ingest latest work orders",
                    "Get new OTs",
                ],
            },
            "plan_ots": {
                "description": "Plan and assign work orders to teams",
                "keywords": ["plan", "assign", "asignación", "planificar", "distribuir"],
                "example_inputs": [
                    "Plan unassigned OTs",
                    "Assign work orders to teams",
                    "Optimize team assignments",
                ],
            },
            "check_governance": {
                "description": "Check inactive work orders and manage auto-cancellation",
                "keywords": ["governance", "check", "inactivity", "cancel", "revisar", "verificar"],
                "example_inputs": [
                    "Check inactive OTs",
                    "Run governance checks",
                    "Auto-cancel old orders",
                ],
            },
            "send_notification": {
                "description": "Send notifications and alerts",
                "keywords": ["notify", "alert", "send", "notificar", "alertar", "enviar"],
                "example_inputs": [
                    "Send alert about OT status",
                    "Notify team of assignment",
                    "Send reminder",
                ],
            },
            "query": {
                "description": "General information queries",
                "keywords": ["how", "what", "where", "when", "why", "cuántos", "cuál"],
                "example_inputs": [
                    "How many OTs are pending?",
                    "What is the status of OT-123?",
                    "Show team workload",
                ],
            },
        }

