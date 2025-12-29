"""Graph routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from graph_service.database import get_db
from graph_service.services import GraphService
from graph_service.tasks import rebuild_case_graph


router = APIRouter(tags=["Graphs"])


# Response Models
class GraphNode(BaseModel):
    """Graph node model."""
    id: str
    label: str
    type: str
    iri: str
    source: str
    properties: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Graph edge model."""
    source: str
    target: str
    label: str
    type: str


class GraphLayout(BaseModel):
    """Graph layout model."""
    positions: dict = Field(
        default_factory=dict,
        description="Node positions keyed by node ID",
    )


class CaseGraphResponse(BaseModel):
    """Case graph response."""
    graph_snapshot_id: UUID
    case_id: UUID
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    layout: dict
    depth: int
    include_inferred: bool
    metadata: dict = Field(default_factory=dict)
    created_at: str


class RebuildGraphResponse(BaseModel):
    """Rebuild graph response."""
    task_id: str
    case_id: UUID
    status: str = "pending"
    message: str = "Graph rebuild started"


class TaskStatusResponse(BaseModel):
    """Task status response."""
    task_id: str
    status: str
    result: dict | None = None


@router.get("/cases/{case_id}/graph", response_model=CaseGraphResponse)
async def get_case_graph(
    case_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    depth: int = Query(2, ge=1, le=5, description="Graph traversal depth"),
    include_inferred: bool = Query(True, description="Include inferred relationships"),
) -> CaseGraphResponse:
    """Get case graph.

    Retrieves the latest graph snapshot for the specified case with given parameters.
    If no matching snapshot exists, returns 404.
    """
    graph_service = GraphService(db)

    snapshot = await graph_service.get_latest_snapshot(
        case_id=case_id,
        depth=depth,
        include_inferred=include_inferred,
    )

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No graph snapshot found for case {case_id} "
            f"with depth={depth}, include_inferred={include_inferred}",
        )

    return CaseGraphResponse(
        graph_snapshot_id=snapshot.graph_snapshot_id,
        case_id=snapshot.case_id,
        nodes=[GraphNode(**node) for node in snapshot.nodes],
        edges=[GraphEdge(**edge) for edge in snapshot.edges],
        layout=snapshot.layout,
        depth=snapshot.depth,
        include_inferred=snapshot.include_inferred,
        metadata=snapshot.metadata_,
        created_at=snapshot.created_at.isoformat(),
    )


@router.post("/cases/{case_id}/graph:rebuild", response_model=RebuildGraphResponse)
async def rebuild_graph(
    case_id: UUID,
    depth: int = Query(2, ge=1, le=5, description="Graph traversal depth"),
    include_inferred: bool = Query(True, description="Include inferred relationships"),
) -> RebuildGraphResponse:
    """Rebuild case graph asynchronously.

    Triggers a Celery task to rebuild the case graph using the GraphAssembler
    LangGraph workflow. Returns immediately with a task ID that can be used
    to check status.
    """
    # Trigger Celery task
    task = rebuild_case_graph.delay(
        case_id=str(case_id),
        depth=depth,
        include_inferred=include_inferred,
    )

    return RebuildGraphResponse(
        task_id=task.id,
        case_id=case_id,
        status="pending",
        message=f"Graph rebuild started for case {case_id}",
    )


@router.get("/graphs/{graph_snapshot_id}", response_model=CaseGraphResponse)
async def get_graph_snapshot(
    graph_snapshot_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CaseGraphResponse:
    """Get specific graph snapshot by ID.

    Retrieves a specific graph snapshot regardless of whether it's the latest.
    Useful for viewing historical graph states.
    """
    graph_service = GraphService(db)

    snapshot = await graph_service.get_snapshot_by_id(graph_snapshot_id)

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Graph snapshot {graph_snapshot_id} not found",
        )

    return CaseGraphResponse(
        graph_snapshot_id=snapshot.graph_snapshot_id,
        case_id=snapshot.case_id,
        nodes=[GraphNode(**node) for node in snapshot.nodes],
        edges=[GraphEdge(**edge) for edge in snapshot.edges],
        layout=snapshot.layout,
        depth=snapshot.depth,
        include_inferred=snapshot.include_inferred,
        metadata=snapshot.metadata_,
        created_at=snapshot.created_at.isoformat(),
    )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get Celery task status.

    Checks the status of a graph rebuild task. Returns task status and result
    if completed.
    """
    from graph_service.tasks import celery_app

    task_result = celery_app.AsyncResult(task_id)

    response = TaskStatusResponse(
        task_id=task_id,
        status=task_result.status.lower(),
    )

    if task_result.successful():
        response.result = task_result.result
    elif task_result.failed():
        response.result = {"error": str(task_result.info)}

    return response
