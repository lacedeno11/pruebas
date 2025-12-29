"""Graph Service business logic."""

from uuid import UUID
from typing import List

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from graph_service.models import CaseGraphSnapshot


class GraphService:
    """Service for managing case graph snapshots."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def get_latest_snapshot(
        self,
        case_id: UUID,
        depth: int | None = None,
        include_inferred: bool | None = None,
    ) -> CaseGraphSnapshot | None:
        """Get latest graph snapshot for a case with optional filters."""
        query = select(CaseGraphSnapshot).where(CaseGraphSnapshot.case_id == case_id)

        if depth is not None:
            query = query.where(CaseGraphSnapshot.depth == depth)

        if include_inferred is not None:
            query = query.where(CaseGraphSnapshot.include_inferred == include_inferred)

        query = query.order_by(desc(CaseGraphSnapshot.created_at))
        result = await self.db.execute(query)
        return result.scalars().first()

    async def get_snapshot_by_id(self, graph_snapshot_id: UUID) -> CaseGraphSnapshot | None:
        """Get a specific graph snapshot by ID."""
        result = await self.db.execute(
            select(CaseGraphSnapshot).where(
                CaseGraphSnapshot.graph_snapshot_id == graph_snapshot_id
            )
        )
        return result.scalars().first()

    async def list_snapshots(
        self,
        case_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[CaseGraphSnapshot], int]:
        """List all snapshots for a case with pagination."""
        # Get total count
        count_query = select(CaseGraphSnapshot).where(CaseGraphSnapshot.case_id == case_id)
        result = await self.db.execute(count_query)
        total = len(result.scalars().all())

        # Get paginated results
        query = (
            select(CaseGraphSnapshot)
            .where(CaseGraphSnapshot.case_id == case_id)
            .order_by(desc(CaseGraphSnapshot.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        snapshots = result.scalars().all()

        return list(snapshots), total

    async def create_snapshot(
        self,
        case_id: UUID,
        nodes: list,
        edges: list,
        layout: dict,
        depth: int = 2,
        include_inferred: bool = True,
        metadata: dict | None = None,
        task_id: str | None = None,
    ) -> CaseGraphSnapshot:
        """Create a new graph snapshot."""
        snapshot = CaseGraphSnapshot(
            case_id=case_id,
            nodes=nodes,
            edges=edges,
            layout=layout,
            depth=depth,
            include_inferred=include_inferred,
            metadata_=metadata or {},
            task_id=task_id,
        )

        self.db.add(snapshot)
        await self.db.flush()
        await self.db.refresh(snapshot)

        return snapshot

    async def update_snapshot(
        self,
        graph_snapshot_id: UUID,
        nodes: list | None = None,
        edges: list | None = None,
        layout: dict | None = None,
        metadata: dict | None = None,
    ) -> CaseGraphSnapshot | None:
        """Update an existing graph snapshot."""
        snapshot = await self.get_snapshot_by_id(graph_snapshot_id)

        if not snapshot:
            return None

        if nodes is not None:
            snapshot.nodes = nodes
        if edges is not None:
            snapshot.edges = edges
        if layout is not None:
            snapshot.layout = layout
        if metadata is not None:
            snapshot.metadata_ = metadata

        await self.db.flush()
        await self.db.refresh(snapshot)

        return snapshot
