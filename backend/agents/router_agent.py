"""
RouterAgent - Classifies user input and system events.
Routes requests to appropriate agent based on input classification.
"""

from typing import Optional

# from langchain.chat_models import ChatOpenAI
# from langchain.prompts import ChatPromptTemplate
# from langchain.schema.output_parser import StrOutputParser


class RouterAgent:
    """
    RouterAgent classifies user input into categories for agent routing.
    
    Classification categories:
    - INGEST_OT: Fetch and register new OTs from TELCOS
    - PLAN_OTS: Trigger automatic planning algorithm
    - CHECK_STATUS: Query OT status and related information
    - MANUAL_ASSIGNMENT: Manually assign OT to crew
    - QUERY: General information queries
    """

    def __init__(self, llm: Optional[object] = None):
        """
        Initialize RouterAgent with LLM instance.

        Args:
            llm: OpenAI LLM instance (or compatible)
        """
        self.llm = llm
        # TODO: Initialize prompt template and output parser

    async def classify_input(self, user_input: str) -> str:
        """
        Classify user input into agent routing categories.

        Args:
            user_input: User message or system event

        Returns:
            Classification string: INGEST_OT, PLAN_OTS, CHECK_STATUS, MANUAL_ASSIGNMENT, or QUERY
        """
        # TODO: Implement LLM-based classification
        # For now, use simple keyword matching
        user_input_lower = user_input.lower()

        if any(
            keyword in user_input_lower
            for keyword in ["ingest", "fetch", "download", "import", "pull"]
        ):
            return "INGEST_OT"

        if any(
            keyword in user_input_lower
            for keyword in ["plan", "assign", "planning", "distribute", "balance"]
        ):
            return "PLAN_OTS"

        if any(
            keyword in user_input_lower
            for keyword in ["status", "state", "check", "verify", "view"]
        ):
            return "CHECK_STATUS"

        if any(
            keyword in user_input_lower
            for keyword in ["assign", "manual", "crew", "cuadrilla"]
        ):
            return "MANUAL_ASSIGNMENT"

        return "QUERY"

