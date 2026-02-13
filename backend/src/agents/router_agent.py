"""
Router Agent for PEI Platform.

The RouterAgent is the entry point for the multi-agent system. It analyzes
user input and routes it to the appropriate specialized agent based on the
user's intent.

Routing categories:
- ingest_ots: Download new OTs from external API
- plan_ots: Assign cuadrillas to OTs
- check_governance: Review alerts and auto-cancellations
- manual_transition: User wants to change OT status
- query_status: Information request about OTs or cuadrillas
"""

import json
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_agent import BaseAgent
from src.agents.state import PEIState

logger = logging.getLogger(__name__)


class RouterAgent(BaseAgent):
    """
    Router Agent for intent classification and routing.

    The RouterAgent is responsible for:
    1. Analyzing user input to understand intent
    2. Classifying the request into one of 5 categories
    3. Setting routing decision in state metadata
    4. Passing control to appropriate specialized agent

    Routes:
    - ingest_ots: OTSAgent - downloads and ingests new OTs
    - plan_ots: PlanificacionAgent - assigns OTs to cuadrillas
    - check_governance: GobernanzaAgent - checks governance rules and alerts
    - manual_transition: GobernanzaAgent - validates status transition
    - query_status: Returns OT information (could be dashboard endpoint)

    Confidence scoring:
    - 0.9-1.0: Very confident in classification
    - 0.7-0.9: Confident
    - 0.5-0.7: Moderately confident
    - <0.5: Low confidence (may require human intervention)
    """

    def __init__(self, db: AsyncSession, llm=None):
        """Initialize the RouterAgent."""
        super().__init__(db, llm, agent_name="RouterAgent")

    def _create_system_prompt(self) -> str:
        """
        Create the system prompt for the Router Agent.

        Returns:
            str: System prompt text
        """
        return """You are the Router Agent for the PEI work order management system.
Your job is to classify user requests into one of these categories:

1. ingest_ots: When user wants to download/ingest new work orders from the API
   Examples: "Download new OTs", "Fetch pending work orders", "Ingest OTs from Telcos"

2. plan_ots: When user wants to assign work orders to teams (cuadrillas)
   Examples: "Plan OTs", "Assign work orders", "Run planning algorithm", "Distribute OTs to teams"

3. check_governance: When user wants to check governance rules, alerts, or auto-cancellations
   Examples: "Check alerts", "Review governance", "Check detention status", "Show governance alerts"

4. manual_transition: When user wants to manually change an OT status
   Examples: "Mark OT as detained", "Cancel OT", "Change OT status", "Update OT state"

5. query_status: When user is asking for information about OTs or cuadrillas
   Examples: "List OTs", "Show OT details", "What's the status of OT-123", "Show team information"

Always respond with a JSON object containing:
{
    "route": "<one of the 5 routes>",
    "confidence": <0.0 to 1.0>,
    "reasoning": "<brief explanation of classification>"
}"""

    async def process(self, state: PEIState) -> PEIState:
        """
        Process user input and route to appropriate agent.

        Args:
            state (PEIState): Current workflow state with user input

        Returns:
            PEIState: Updated state with routing decision in metadata
        """
        try:
            # Validate state
            if not await self.validate_state(state):
                return await self.handle_error(state, "Invalid state for RouterAgent")

            user_input = state.get("input", "").strip()
            logger.info(f"RouterAgent processing input: {user_input[:100]}")

            # Default routing based on keyword matching if LLM is not available
            if not self.llm:
                route_decision = self._classify_by_keywords(user_input)
            else:
                # Use LLM for classification
                try:
                    route_decision = await self._classify_with_llm(user_input)
                except Exception as e:
                    logger.warning(
                        f"RouterAgent: LLM classification failed, falling back to keywords: {str(e)}"
                    )
                    route_decision = self._classify_by_keywords(user_input)

            # Set routing decision in metadata
            state["metadata"]["route"] = route_decision.get("route", "query_status")
            state["metadata"]["confidence"] = route_decision.get("confidence", 0.5)
            state["metadata"]["routing_reasoning"] = route_decision.get("reasoning", "")

            # Add message to history
            state["agent_messages"].append({
                "agent": "RouterAgent",
                "content": f"Classified intent as '{route_decision.get('route')}' with confidence {route_decision.get('confidence'):.2f}",
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Log the routing decision
            await self.log_action(
                accion=f"Routing decision: {route_decision.get('route')} (confidence: {route_decision.get('confidence'):.2f})",
                resultado="SUCCESS",
                metadata={
                    "route": route_decision.get("route"),
                    "confidence": route_decision.get("confidence"),
                    "reasoning": route_decision.get("reasoning"),
                },
            )

            # Set action result
            state["action_result"] = {
                "success": True,
                "message": f"Request routed to {route_decision.get('route')}",
                "data": {
                    "route": route_decision.get("route"),
                    "confidence": route_decision.get("confidence"),
                },
            }

            logger.info(
                f"RouterAgent: Routed to '{route_decision.get('route')}' "
                f"(confidence: {route_decision.get('confidence'):.2f})"
            )

            return state

        except Exception as e:
            logger.error(f"RouterAgent error: {str(e)}", exc_info=True)
            return await self.handle_error(state, f"RouterAgent error: {str(e)}")

    async def _classify_with_llm(self, user_input: str) -> dict:
        """
        Use LLM to classify user input.

        Args:
            user_input (str): User's input text

        Returns:
            dict: Classification result with route, confidence, and reasoning
        """
        try:
            # Create prompt
            prompt = f"""Classify this user request:
"{user_input}"

Respond ONLY with valid JSON (no other text)."""

            # Get LLM response
            system_prompt = self._create_system_prompt()
            response = await self.llm.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
            )

            # Parse response
            response_text = response.content.strip()

            # Try to extract JSON from response
            try:
                # Handle markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text

                classification = json.loads(json_str)

                # Validate required fields
                if "route" not in classification:
                    return self._classify_by_keywords(user_input)

                # Ensure confidence is between 0 and 1
                confidence = classification.get("confidence", 0.5)
                confidence = max(0.0, min(1.0, confidence))
                classification["confidence"] = confidence

                return classification

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM JSON response: {str(e)}")
                return self._classify_by_keywords(user_input)

        except Exception as e:
            logger.error(f"LLM classification error: {str(e)}")
            return self._classify_by_keywords(user_input)

    def _classify_by_keywords(self, user_input: str) -> dict:
        """
        Fallback keyword-based classification.

        Args:
            user_input (str): User's input text

        Returns:
            dict: Classification result with route, confidence, and reasoning
        """
        user_input_lower = user_input.lower()

        # Define keyword patterns for each route
        ingest_keywords = ["ingest", "download", "fetch", "pull", "import", "get ots", "new ots"]
        plan_keywords = ["plan", "assign", "planning", "cuadrilla", "distribute", "allocate"]
        governance_keywords = ["govern", "alert", "detention", "cancel", "check", "review", "status check"]
        transition_keywords = ["transition", "change status", "mark", "detention reason", "detained"]
        query_keywords = ["list", "show", "get", "query", "info", "details", "what", "how many"]

        # Check matches
        routes = []

        if any(keyword in user_input_lower for keyword in ingest_keywords):
            routes.append(("ingest_ots", 0.9))

        if any(keyword in user_input_lower for keyword in plan_keywords):
            routes.append(("plan_ots", 0.9))

        if any(keyword in user_input_lower for keyword in governance_keywords):
            routes.append(("check_governance", 0.85))

        if any(keyword in user_input_lower for keyword in transition_keywords):
            routes.append(("manual_transition", 0.85))

        if any(keyword in user_input_lower for keyword in query_keywords):
            routes.append(("query_status", 0.75))

        # Default to query_status if no matches
        if not routes:
            return {
                "route": "query_status",
                "confidence": 0.5,
                "reasoning": "No clear intent detected, defaulting to query",
            }

        # Sort by confidence and return highest
        routes.sort(key=lambda x: x[1], reverse=True)
        best_route, confidence = routes[0]

        return {
            "route": best_route,
            "confidence": confidence,
            "reasoning": f"Matched keywords for {best_route}",
        }

    async def can_route_to(self, route: str) -> bool:
        """
        Check if the router can route to a specific agent.

        Args:
            route (str): Route name to check

        Returns:
            bool: True if route is valid, False otherwise
        """
        valid_routes = [
            "ingest_ots",
            "plan_ots",
            "check_governance",
            "manual_transition",
            "query_status",
        ]
        return route in valid_routes

