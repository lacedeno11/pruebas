"""
RouterAgent for PEI Platform agentic system.
Routes user requests and system events to appropriate agents based on intent analysis.
"""

from typing import Dict
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI

from backend.agents.base_agent import BaseAgent
from backend.models.log_agente import ActionResult


class RouterAgent(BaseAgent):
    """
    RouterAgent that analyzes user input and routes to appropriate agents.

    The RouterAgent is the entry point for all graph executions. It receives:
    - user_input: Natural language request from user or system event
    - event_type: Type of event (user_input, scheduled_governance, etc.)

    Based on the user_input and event_type, RouterAgent classifies the intent
    and determines which agent should handle the request next.

    Routing Logic:
    - 'ots' agent: Download, sync, or fetch OT data from TELCOS
    - 'planificacion' agent: Plan, assign, or balance OT assignments
    - 'gobernanza' agent: Check governance rules, alerts, cancellations
    - 'comunicacion' agent: Send notifications, communicate status changes
    - 'end': Terminate graph execution (no further processing needed)

    Examples:
    - "Download new OTs from TELCOS" → 'ots'
    - "Plan assignments for unassigned OTs" → 'planificacion'
    - "Check for inactive OTs" → 'gobernanza'
    - "Send notification to coordinators" → 'comunicacion'
    - Scheduled governance event → 'gobernanza'
    - Nightly normalization → 'planificacion'
    """

    def __init__(self, llm: ChatOpenAI, db_session: Session):
        """
        Initialize RouterAgent.

        Args:
            llm: ChatOpenAI instance for LLM-based intent classification
            db_session: SQLAlchemy session for database operations
        """
        super().__init__(llm, db_session)
        self.agent_name = "RouterAgent"

    async def execute(self, state: Dict) -> Dict:
        """
        Route user input or system event to appropriate agent.

        Analyzes the user_input and event_type to determine which agent
        should handle the request. Uses LLM for intent classification when
        the intent is ambiguous.

        Args:
            state: Graph state containing:
                - user_input (str): User request or description
                - event_type (str): Type of event
                - Other state fields passed through

        Returns:
            Updated state with 'next_agent' field set to one of:
            - 'ots': Route to OTSAgent for downloading/syncing OTs
            - 'planificacion': Route to PlanificacionAgent for assignment/planning
            - 'gobernanza': Route to GobernanzaAgent for governance checks
            - 'comunicacion': Route to ComunicacionAgent for notifications
            - 'end': Terminate graph execution
        """
        user_input = state.get("user_input", "").lower()
        event_type = state.get("event_type", "").lower()

        # Determine next agent based on event type and user input
        next_agent = self._classify_intent(user_input, event_type)

        # Log the routing decision
        self._log_action(
            agente_name="RouterAgent",
            accion="classify_and_route",
            resultado=ActionResult.SUCCESS,
            metadata={
                "user_input": user_input[:100],  # First 100 chars for logging
                "event_type": event_type,
                "next_agent": next_agent,
            },
        )

        # Return updated state with next agent
        return {
            **state,
            "next_agent": next_agent,
            "action_result": f"Routed to {next_agent} agent",
        }

    def _classify_intent(self, user_input: str, event_type: str) -> str:
        """
        Classify the intent based on user input and event type.

        Implements pattern matching for common requests, then falls back to
        LLM-based classification for ambiguous requests.

        Args:
            user_input: User's natural language request (lowercase)
            event_type: Type of event triggering the classification

        Returns:
            Name of the agent to route to: 'ots', 'planificacion',
            'gobernanza', 'comunicacion', or 'end'
        """
        # Handle scheduled events based on event_type
        if event_type == "scheduled_governance":
            return "gobernanza"
        elif event_type == "nightly_normalization":
            return "planificacion"

        # Pattern matching for common OTS-related requests
        if any(
            keyword in user_input
            for keyword in [
                "download",
                "sync",
                "fetch",
                "get",
                "retrieve",
                "ots",
                "telcos",
            ]
        ):
            if any(keyword in user_input for keyword in ["ot", "telcos", "order"]):
                return "ots"

        # Pattern matching for planning/assignment requests
        if any(
            keyword in user_input
            for keyword in [
                "plan",
                "assign",
                "balance",
                "allocate",
                "distribute",
                "optimize",
                "route",
            ]
        ):
            return "planificacion"

        # Pattern matching for governance/alert requests
        if any(
            keyword in user_input
            for keyword in [
                "check",
                "alert",
                "cancel",
                "monitor",
                "inactive",
                "detention",
                "govern",
                "validate",
                "document",
            ]
        ):
            return "gobernanza"

        # Pattern matching for communication/notification requests
        if any(
            keyword in user_input
            for keyword in [
                "send",
                "notify",
                "communicate",
                "message",
                "email",
                "telegram",
                "inform",
                "contact",
            ]
        ):
            return "comunicacion"

        # If no pattern matches, use LLM for classification
        return self._llm_classify_intent(user_input)

    def _llm_classify_intent(self, user_input: str) -> str:
        """
        Use LLM to classify ambiguous requests.

        Sends the user input to the LLM with a prompt asking it to classify
        the intent and determine which agent should handle the request.

        Args:
            user_input: User's natural language request

        Returns:
            Name of the agent: 'ots', 'planificacion', 'gobernanza',
            'comunicacion', or 'end'
        """
        try:
            # Build the classification prompt
            prompt = f"""Classify the following request and determine which agent should handle it.

Request: {user_input}

Classify the request as ONE of these categories:
- 'ots': For downloading, syncing, or fetching OT (work order) data from TELCOS system
- 'planificacion': For planning OT assignments, balancing cuadrillas, or route optimization
- 'gobernanza': For checking governance rules, monitoring alerts, validating documents, or auto-cancelling OTs
- 'comunicacion': For sending notifications, messages, or communicating status changes
- 'end': If no action is needed or request is unclear

Respond with ONLY the agent name (e.g., 'ots', 'planificacion', 'gobernanza', 'comunicacion', or 'end').
Do not include quotes or any other text."""

            # Call LLM for classification
            response = self.llm.invoke(prompt)
            classification = response.content.strip().lower()

            # Validate the response and ensure it's a valid agent name
            valid_agents = ["ots", "planificacion", "gobernanza", "comunicacion", "end"]
            if classification in valid_agents:
                return classification
            else:
                # If LLM returns invalid response, default to 'end'
                print(f"⚠️ Invalid agent classification from LLM: {classification}")
                return "end"

        except Exception as e:
            # If LLM call fails, log the error and default to 'end'
            print(f"❌ Error in LLM classification: {str(e)}")
            self._log_action(
                agente_name="RouterAgent",
                accion="llm_classify_intent",
                resultado=ActionResult.FAILURE,
                metadata={
                    "error": str(e),
                    "user_input": user_input[:100],
                },
            )
            return "end"

