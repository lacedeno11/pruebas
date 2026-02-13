import json
import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class RoutingDecision(BaseModel):
    """Schema for routing decision output."""
    agent: str = Field(
        ...,
        description="Target agent: OTS_AGENT, PLANIFICACION_AGENT, GOBERNANZA_AGENT, or COMUNICACION_AGENT"
    )
    reasoning: str = Field(..., description="Explanation for the routing decision")
    priority: str = Field(default="normal", description="Priority level: low, normal, high, critical")
    requires_db: bool = Field(default=True, description="Whether this request requires database access")


class RouterAgent:
    """
    RouterAgent classifies incoming user messages and system events to route them to the appropriate agent.
    
    Uses LangChain ChatOpenAI with structured output for intelligent classification.
    Routes to one of four agents:
    - OTS_AGENT: For OT ingestion, status updates, and OT-specific operations
    - PLANIFICACION_AGENT: For assignment planning and optimization
    - GOBERNANZA_AGENT: For governance, compliance checks, and alerts
    - COMUNICACION_AGENT: For notifications and communications
    """

    def __init__(self):
        """Initialize RouterAgent with LLM client."""
        try:
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0,
                api_key=settings.OPENAI_API_KEY
            )
        except Exception as e:
            logger.warning(f"Failed to initialize ChatOpenAI: {str(e)}. Using rule-based routing.")
            self.llm = None

    async def route(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify and route the incoming message to the appropriate agent.
        
        Args:
            state: AgentState dictionary with 'input' field containing user message
        
        Returns:
            Updated state with 'action' field set to target agent and routing metadata
        """
        user_input = state.get("input", "").strip()

        if not user_input:
            logger.warning("Empty input received")
            return {
                **state,
                "action": "ERROR",
                "errors": ["Empty input provided"]
            }

        try:
            if self.llm:
                # Use LLM for intelligent routing
                routing_decision = await self._route_with_llm(user_input)
            else:
                # Fall back to rule-based routing
                routing_decision = self._route_with_rules(user_input)

            # Log the routing decision
            logger.info(
                f"Routing decision: {routing_decision.agent} (Priority: {routing_decision.priority}) - {routing_decision.reasoning}"
            )

            return {
                **state,
                "action": routing_decision.agent,
                "metadata": {
                    "reasoning": routing_decision.reasoning,
                    "priority": routing_decision.priority,
                    "requires_db": routing_decision.requires_db
                }
            }

        except Exception as e:
            logger.error(f"Error in routing: {str(e)}")
            return {
                **state,
                "action": "ERROR",
                "errors": [f"Routing error: {str(e)}"]
            }

    async def _route_with_llm(self, user_input: str) -> RoutingDecision:
        """
        Use ChatOpenAI to intelligently classify and route the input.
        
        Args:
            user_input: User message to classify
        
        Returns:
            RoutingDecision with target agent and reasoning
        """
        system_prompt = """You are a routing agent for a work order management system. Classify incoming user messages and determine which agent should handle them.

Agents:
1. OTS_AGENT: Handles OT (Orden de Trabajo) ingestion, creation, updates, status changes, and searches
2. PLANIFICACION_AGENT: Handles work order assignment to teams (cuadrillas), optimization, and planning
3. GOBERNANZA_AGENT: Handles governance checks, compliance, alerts, document validation, and detention monitoring
4. COMUNICACION_AGENT: Handles notifications, alerts, and communications to team managers

Classify the user input and determine:
- Which agent should handle it
- Your reasoning for this choice
- Priority level (low, normal, high, critical)
- Whether database access is needed

Respond with a JSON object containing: agent, reasoning, priority, requires_db"""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User input: {user_input}")
            ])

            # Parse the response as JSON
            response_text = response.content.strip()
            
            # Try to extract JSON from the response
            if "{" in response_text and "}" in response_text:
                json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
                routing_dict = json.loads(json_str)
                return RoutingDecision(**routing_dict)
            else:
                # Fallback if response is not JSON
                logger.warning(f"LLM response was not JSON format: {response_text}")
                return self._route_with_rules(user_input)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            return self._route_with_rules(user_input)
        except Exception as e:
            logger.error(f"LLM routing failed: {str(e)}")
            return self._route_with_rules(user_input)

    def _route_with_rules(self, user_input: str) -> RoutingDecision:
        """
        Rule-based routing fallback when LLM is not available.
        Uses keyword matching to classify input.
        
        Args:
            user_input: User message to classify
        
        Returns:
            RoutingDecision with target agent based on keywords
        """
        user_lower = user_input.lower()

        # OTS_AGENT keywords
        ots_keywords = [
            "crear", "create", "ingresar", "import", "importar",
            "ot", "orden", "trabajo", "work order",
            "estado", "status", "actualizar", "update",
            "cliente", "customer", "login",
            "ubicación", "location", "coordenadas", "coordinates"
        ]

        # PLANIFICACION_AGENT keywords
        planning_keywords = [
            "asignar", "assign", "assignment", "asignación",
            "planificar", "plan", "planning", "planificación",
            "cuadrilla", "equipo", "team", "teams", "crew",
            "ruta", "route", "optimization", "optimización",
            "carga", "load", "distribuir", "distribute"
        ]

        # GOBERNANZA_AGENT keywords
        governance_keywords = [
            "detenida", "detained", "detención", "detention",
            "días", "days", "alerta", "alert", "alertas",
            "cancelar", "cancel", "anular", "cumplimiento", "compliance",
            "documento", "document", "documentos", "documents",
            "preplanificada", "preplanificación",
            "validar", "validate", "validación", "validation"
        ]

        # COMUNICACION_AGENT keywords
        communication_keywords = [
            "notificar", "notify", "notification", "notificación",
            "mensaje", "message", "email", "correo", "telegram",
            "contactar", "contact", "comunicar", "communicate",
            "alerta", "alert", "encargado", "manager", "pm"
        ]

        # Calculate keyword matches
        ots_score = sum(1 for keyword in ots_keywords if keyword in user_lower)
        planning_score = sum(1 for keyword in planning_keywords if keyword in user_lower)
        governance_score = sum(1 for keyword in governance_keywords if keyword in user_lower)
        communication_score = sum(1 for keyword in communication_keywords if keyword in user_lower)

        # Find the agent with highest score
        scores = {
            "OTS_AGENT": ots_score,
            "PLANIFICACION_AGENT": planning_score,
            "GOBERNANZA_AGENT": governance_score,
            "COMUNICACION_AGENT": communication_score
        }

        selected_agent = max(scores, key=scores.get)

        # Default to OTS_AGENT if no clear match
        if all(score == 0 for score in scores.values()):
            selected_agent = "OTS_AGENT"

        return RoutingDecision(
            agent=selected_agent,
            reasoning=f"Rule-based routing selected {selected_agent} based on keyword matching",
            priority="normal",
            requires_db=True
        )

    async def classify_priority(self, message: str) -> str:
        """
        Classify the priority level of a message.
        
        Args:
            message: Message to classify
        
        Returns:
            Priority level: low, normal, high, or critical
        """
        priority_keywords = {
            "critical": ["urgente", "crítico", "critical", "emergency", "emergencia", "immediate", "inmediato"],
            "high": ["importante", "high", "importante", "asap", "rápido", "quick"],
            "low": ["no urgente", "cuando sea", "low", "whenever", "low priority"]
        }

        message_lower = message.lower()

        for priority, keywords in priority_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return priority

        return "normal"

