"""Workflow service for LangGraph integration."""

from typing import Any

from langgraph_workflows.graphs.ehr_ontology import create_ehr_ontology_graph
from langgraph_workflows.graphs.explanation_composer import create_explanation_composer_graph
from langgraph_workflows.state import GraphState

from ehr_service.config import settings


class WorkflowService:
    """Service for running LangGraph workflows."""

    def __init__(self):
        self.ehr_ontology_graph = create_ehr_ontology_graph()
        self.explanation_composer_graph = create_explanation_composer_graph()

    async def run_ehr_to_ontology_workflow(
        self,
        ehr_text: str,
        ehr_id: str,
    ) -> dict[str, Any]:
        """Run the EHR to Ontology workflow.

        Args:
            ehr_text: Raw EHR text to process
            ehr_id: EHR document ID

        Returns:
            dict containing workflow state with outputs
        """
        # Initialize state
        initial_state: GraphState = {
            "execution": {
                "execution_id": f"ehr_{ehr_id}",
                "workflow_name": "EHRToOntologyGraph",
                "status": "pending",
                "progress": 0.0,
            },
            "inputs": {
                "ehr_text": ehr_text,
                "ehr_id": ehr_id,
            },
            "outputs": {},
            "context": {
                "ehr_id": ehr_id,
            },
            "policies": {},
            "_intermediate_results": {},
        }

        # Run workflow
        result = await self.ehr_ontology_graph.ainvoke(initial_state)

        return result

    async def run_explanation_composer_workflow(
        self,
        case_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the Explanation Composer workflow.

        Args:
            case_id: Case ID
            context: Additional context including evidence from various sources

        Returns:
            dict containing workflow state with outputs
        """
        # Initialize state
        initial_state: GraphState = {
            "execution": {
                "execution_id": f"exp_{case_id}",
                "workflow_name": "ExplanationComposerGraph",
                "status": "pending",
                "progress": 0.0,
            },
            "inputs": {
                "case_id": case_id,
            },
            "outputs": context.get("outputs", {}),  # Pre-populate with existing outputs
            "context": {
                "case_id": case_id,
                **context,
            },
            "policies": context.get("policies", {}),
            "_intermediate_results": {},
        }

        # Run workflow
        result = await self.explanation_composer_graph.ainvoke(initial_state)

        return result
