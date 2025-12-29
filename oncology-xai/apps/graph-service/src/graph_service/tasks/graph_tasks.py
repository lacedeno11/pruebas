"""Graph building Celery tasks."""

import asyncio
from uuid import UUID
import logging

from graph_service.tasks.celery_app import celery_app
from graph_service.config import settings
from graph_service.database import async_session_maker
from graph_service.services import GraphService

from langgraph_workflows.graphs.graph_assembler import create_graph_assembler_graph
from langgraph_workflows.state import GraphState

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="graph_service.rebuild_case_graph")
def rebuild_case_graph(
    self,
    case_id: str,
    depth: int = 2,
    include_inferred: bool = True,
) -> dict:
    """Rebuild case graph using LangGraph workflow.

    Args:
        case_id: Case ID to build graph for
        depth: Depth of graph traversal
        include_inferred: Whether to include inferred relationships

    Returns:
        dict with graph_snapshot_id and status
    """
    logger.info(f"Starting graph rebuild for case {case_id} (task {self.request.id})")

    try:
        # Run async workflow
        result = asyncio.run(
            _rebuild_graph_async(
                case_id=case_id,
                depth=depth,
                include_inferred=include_inferred,
                task_id=self.request.id,
            )
        )

        logger.info(f"Graph rebuild completed for case {case_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error rebuilding graph for case {case_id}: {e}", exc_info=True)
        raise


async def _rebuild_graph_async(
    case_id: str,
    depth: int,
    include_inferred: bool,
    task_id: str,
) -> dict:
    """Async graph rebuild implementation."""

    # Initialize LangGraph workflow
    workflow = create_graph_assembler_graph()

    # Create initial state
    initial_state: GraphState = {
        "context": {
            "case_id": case_id,
            "depth": depth,
            "include_inferred": include_inferred,
        },
        "execution": {
            "run_id": task_id,
            "status": "pending",
            "progress": 0.0,
        },
        "_intermediate_results": {},
        "outputs": {},
    }

    # Run workflow
    final_state = await workflow.ainvoke(initial_state)

    # Check if workflow succeeded
    if final_state["execution"]["status"] != "completed":
        error = final_state["execution"].get("error", {})
        raise RuntimeError(
            f"Workflow failed: {error.get('message', 'Unknown error')}"
        )

    # Extract outputs
    outputs = final_state.get("outputs", {})
    nodes = outputs.get("nodes", [])
    edges = outputs.get("edges", [])
    intermediate = final_state.get("_intermediate_results", {})
    layout = intermediate.get("layout", {})
    provenance = intermediate.get("provenance", [])

    # Save snapshot to database
    async with async_session_maker() as session:
        try:
            graph_service = GraphService(session)

            snapshot = await graph_service.create_snapshot(
                case_id=UUID(case_id),
                nodes=nodes,
                edges=edges,
                layout=layout,
                depth=depth,
                include_inferred=include_inferred,
                metadata={
                    "provenance": provenance,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                    "workflow_run_id": task_id,
                },
                task_id=task_id,
            )

            await session.commit()

            return {
                "graph_snapshot_id": str(snapshot.graph_snapshot_id),
                "case_id": str(snapshot.case_id),
                "status": "completed",
                "node_count": len(nodes),
                "edge_count": len(edges),
            }

        except Exception as e:
            await session.rollback()
            raise
