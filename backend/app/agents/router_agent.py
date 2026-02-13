"""RouterAgent for intent classification and routing."""

import logging
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.state import AgentState
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RouterAgent(BaseAgent):
    """Routes user input to appropriate agent based on intent classification."""

    async def execute(self, state: AgentState) -> AgentState:
        """Classify intent and determine next agent."""
        try:
            # Get user message
            messages = state.get("messages", [])
            user_message = state.get("input_data", {}).get("user_message", "")
            
            if not user_message:
                return self._update_state(state, error="No user message provided")
            
            # Simple intent classification (can be enhanced with LLM)
            action_type = self._classify_intent(user_message)
            
            # Update state with classified action
            state["action_type"] = action_type
            state["should_continue"] = True
            state["agent_history"].append(self.agent_name)
            
            self.log_action(
                action="CLASSIFY_INTENT",
                resultado="success",
                metadata={"action_type": action_type, "message": user_message[:100]}
            )
            
            logger.info(f"RouterAgent: Classified intent as {action_type}")
            return state
            
        except Exception as e:
            logger.error(f"RouterAgent error: {str(e)}", exc_info=True)
            return self._update_state(state, error=str(e), should_continue=False)

    def _classify_intent(self, message: str) -> str:
        """Simple keyword-based intent classification."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["sync", "ingest", "fetch", "import"]):
            return "INGEST_OT"
        elif any(word in message_lower for word in ["plan", "assign", "schedule", "organize"]):
            return "PLAN_OT"
        elif any(word in message_lower for word in ["status", "update", "change", "set"]):
            return "UPDATE_STATUS"
        elif any(word in message_lower for word in ["show", "get", "list", "find", "query"]):
            return "QUERY_STATUS"
        elif any(word in message_lower for word in ["governance", "check", "rules", "compliance"]):
            return "GOVERNANCE_CHECK"
        else:
            return "CHAT"

