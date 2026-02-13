"""Router agent for classifying and routing work order requests."""

from backend.graph.state import PEIState, ActionType
from backend.database.models import AgentLog
from backend.database.db import SessionLocal
import os
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Try to import LLM providers
try:
    from langchain_openai import ChatOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from langchain_anthropic import ChatAnthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


ROUTING_PROMPT = """You are a routing agent for a work order management system. 
Classify the user request or system event into one of these actions:

INGEST - Download new OTs from TELCOS API, validate them, and add to database
PLAN - Assign OTs to crews using the 3-phase planning algorithm
VALIDATE - Check business rules (state transitions, crew capacity, document requirements)
NOTIFY - Send alerts and notifications to users
GOVERNANCE - Check timeout rules and auto-cancel old OTs
CHAT - Answer questions about the system or provide information

User request or system event:
{input}

Return ONLY the action name (INGEST, PLAN, VALIDATE, NOTIFY, GOVERNANCE, or CHAT) in uppercase."""


def _get_llm_provider():
    """
    Get the configured LLM provider (OpenAI or Anthropic).
    
    Returns:
        LLM instance or None if no provider is configured
    """
    llm_model = os.getenv("LLM_MODEL", "gpt-4")
    
    # Try OpenAI first
    if HAS_OPENAI and "gpt" in llm_model.lower():
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            return ChatOpenAI(model_name=llm_model, api_key=openai_key, temperature=0)
    
    # Try Anthropic
    if HAS_ANTHROPIC and "claude" in llm_model.lower():
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            return ChatAnthropic(model_name=llm_model, api_key=anthropic_key, temperature=0)
    
    # Fallback: use rule-based routing
    logger.warning("No LLM provider configured, falling back to rule-based routing")
    return None


def _classify_action_rule_based(user_input: str) -> str:
    """
    Classify action based on simple rule-based keyword matching.
    
    Fallback when no LLM is available.
    
    Args:
        user_input: User message or system event
    
    Returns:
        str: Action name (INGEST, PLAN, VALIDATE, NOTIFY, GOVERNANCE, or CHAT)
    """
    user_lower = user_input.lower()
    
    # Check for INGEST keywords
    if any(keyword in user_lower for keyword in ["ingest", "sync", "fetch", "download", "import", "traer"]):
        return ActionType.INGEST.value
    
    # Check for PLAN keywords
    if any(keyword in user_lower for keyword in ["plan", "assign", "asigna", "planifica", "allocate", "distribute"]):
        return ActionType.PLAN.value
    
    # Check for VALIDATE keywords
    if any(keyword in user_lower for keyword in ["validate", "check", "verifica", "validar", "confirm"]):
        return ActionType.VALIDATE.value
    
    # Check for GOVERNANCE keywords
    if any(keyword in user_lower for keyword in ["governance", "timeout", "cancel", "anula", "detenida", "auto"]):
        return ActionType.GOVERNANCE.value
    
    # Check for NOTIFY keywords
    if any(keyword in user_lower for keyword in ["notify", "alert", "alerta", "send", "notify", "message"]):
        return ActionType.NOTIFY.value
    
    # Default to CHAT for questions
    return ActionType.CHAT.value


async def router_node(state: PEIState) -> PEIState:
    """
    Router node that classifies incoming requests into action types.
    
    This node analyzes the current state and determines what action should be executed next.
    It uses an LLM to classify intent if the action is not explicitly set.
    
    Args:
        state: Current PEIState containing messages and/or action field
    
    Returns:
        Updated PEIState with action classified
    
    Behavior:
    - If state.action is already set, returns state unchanged
    - If state.messages exists, uses most recent message for classification
    - Falls back to rule-based classification if LLM unavailable
    - Logs classification to AgentLog for audit trail
    """
    
    # If action is already explicitly set, return immediately
    if state.get("action"):
        logger.info(f"Action already set: {state['action']}")
        return state
    
    # Determine input for classification
    classification_input = ""
    
    # Check if there are messages to classify
    if state.get("messages") and len(state["messages"]) > 0:
        # Get the most recent message
        last_message = state["messages"][-1]
        if last_message.get("role") == "user":
            classification_input = last_message.get("content", "")
    
    # Check if there's OT data
    if not classification_input and state.get("ot_data"):
        classification_input = f"Process OT: {state['ot_data']}"
    
    # Default if nothing found
    if not classification_input:
        classification_input = "System event"
    
    try:
        # Try to use LLM for classification
        llm = _get_llm_provider()
        
        if llm:
            logger.info("Using LLM-based routing")
            prompt = ROUTING_PROMPT.format(input=classification_input)
            response = llm.invoke(prompt)
            classified_action = response.content.strip().upper()
        else:
            logger.info("Using rule-based routing")
            classified_action = _classify_action_rule_based(classification_input)
        
        # Validate classified action
        valid_actions = [action.value.upper() for action in ActionType]
        if classified_action not in valid_actions:
            logger.warning(f"Invalid action classified: {classified_action}, defaulting to CHAT")
            classified_action = ActionType.CHAT.value
        else:
            classified_action = classified_action.lower()
        
        # Log classification
        db = SessionLocal()
        try:
            agent_log = AgentLog(
                ot_id=state.get("ot_id"),
                agente_name="Router Agent",
                accion="Classify Request",
                resultado=f"Classified as: {classified_action}",
                raw_llm_response=classification_input[:500],  # Store input for reference
                timestamp=datetime.utcnow(),
            )
            db.add(agent_log)
            db.commit()
            logger.info(f"Logged classification: {classified_action}")
        finally:
            db.close()
        
        # Update state with classified action
        state["action"] = classified_action
        logger.info(f"Router classified request as: {classified_action}")
        
        return state
    
    except Exception as e:
        logger.error(f"Router agent error: {str(e)}")
        
        # Fallback to rule-based classification on error
        try:
            classified_action = _classify_action_rule_based(classification_input)
            state["action"] = classified_action
            logger.info(f"Fallback router classified as: {classified_action}")
            return state
        except Exception as fallback_error:
            logger.error(f"Fallback router failed: {str(fallback_error)}")
            state["action"] = ActionType.CHAT.value
            state["error"] = f"Router classification failed: {str(e)}"
            return state


def get_action_description(action: str) -> str:
    """
    Get a human-readable description of an action.
    
    Args:
        action: Action name (e.g., 'ingest', 'plan')
    
    Returns:
        str: Human-readable description
    """
    descriptions = {
        ActionType.INGEST.value: "Downloading and validating work orders from TELCOS API",
        ActionType.PLAN.value: "Assigning work orders to crews using the planning algorithm",
        ActionType.VALIDATE.value: "Validating business rules and constraints",
        ActionType.NOTIFY.value: "Sending alerts and notifications to users",
        ActionType.GOVERNANCE.value: "Checking governance rules and auto-cancelling old orders",
        ActionType.CHAT.value: "Answering questions and providing information",
    }
    return descriptions.get(action, "Unknown action")


