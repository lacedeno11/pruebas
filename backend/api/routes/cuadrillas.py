"""
Cuadrilla (Work Team) API routes for the PEI Platform.
Provides endpoints for cuadrilla management, assignment, and rebalancing.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.models import Cuadrilla, OT
from backend.models.cuadrilla import CuadrillaType
from backend.schemas import CuadrillaCreate, CuadrillaResponse, CuadrillaWithOTs
from backend.config import get_settings

# Note: PEIGraphRunner will be imported after agents are created
# from backend.agents.graph_runner import PEIGraphRunner

router = APIRouter(prefix="/api/cuadrillas", tags=["cuadrillas"])


@router.get("", response_model=List[CuadrillaResponse])
async def list_cuadrillas(
    db: Session = Depends(get_db),
    type: Optional[str] = Query(None, description="Filter by cuadrilla type (PRINCIPAL or RESERVA)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> List[CuadrillaResponse]:
    """
    List all cuadrillas with optional filtering.

    Query Parameters:
        - type: Filter by cuadrilla type (PRINCIPAL or RESERVA)
        - is_active: Filter by active status (true/false)

    Returns:
        List of CuadrillaResponse objects matching the filters
    """
    query = db.query(Cuadrilla)

    # Apply filters if provided
    if type:
        try:
            query = query.filter(Cuadrilla.type == CuadrillaType[type.upper()])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid cuadrilla type: {type}")

    if is_active is not None:
        query = query.filter(Cuadrilla.is_active == is_active)

    cuadrillas = query.all()
    return cuadrillas


@router.get("/{cuadrilla_id}", response_model=CuadrillaWithOTs)
async def get_cuadrilla(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
) -> CuadrillaWithOTs:
    """
    Get a single cuadrilla by ID with all assigned OTs.

    Path Parameters:
        - cuadrilla_id: ID of the cuadrilla to retrieve

    Returns:
        CuadrillaWithOTs object containing cuadrilla details and assigned OTs

    Raises:
        404: Cuadrilla not found
    """
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    if not cuadrilla:
        raise HTTPException(
            status_code=404,
            detail=f"Cuadrilla with id {cuadrilla_id} not found",
        )
    return cuadrilla


@router.post("", response_model=CuadrillaResponse)
async def create_cuadrilla(
    cuadrilla_create: CuadrillaCreate,
    db: Session = Depends(get_db),
) -> CuadrillaResponse:
    """
    Create a new cuadrilla (work team).

    Request Body:
        - name: Unique name of the cuadrilla (required)
        - type: Type of cuadrilla: PRINCIPAL or RESERVA (required)
        - daily_capacity: Maximum OTs per day (optional, defaults from config)

    Returns:
        CuadrillaResponse object of the created cuadrilla

    Raises:
        400: Name already exists or invalid type
    """
    # Check if name already exists
    existing = db.query(Cuadrilla).filter(Cuadrilla.name == cuadrilla_create.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Cuadrilla with name '{cuadrilla_create.name}' already exists",
        )

    # Use provided daily_capacity or get from config
    settings = get_settings()
    daily_capacity = (
        cuadrilla_create.daily_capacity
        if cuadrilla_create.daily_capacity is not None
        else settings.CUADRILLA_DAILY_CAPACITY
    )

    # Create new cuadrilla
    cuadrilla = Cuadrilla(
        name=cuadrilla_create.name,
        type=cuadrilla_create.type,
        daily_capacity=daily_capacity,
        current_load=0,
        is_active=True,
    )

    # Persist to database
    db.add(cuadrilla)
    db.commit()
    db.refresh(cuadrilla)

    return cuadrilla


@router.patch("/{cuadrilla_id}", response_model=CuadrillaResponse)
async def update_cuadrilla(
    cuadrilla_id: int,
    cuadrilla_update: dict,
    db: Session = Depends(get_db),
) -> CuadrillaResponse:
    """
    Update cuadrilla details.

    Path Parameters:
        - cuadrilla_id: ID of the cuadrilla to update

    Request Body (all optional):
        - name: New name for the cuadrilla
        - type: New type (PRINCIPAL or RESERVA)
        - daily_capacity: New daily capacity
        - is_active: Active status (true/false)

    Returns:
        Updated CuadrillaResponse object

    Raises:
        404: Cuadrilla not found
        400: Name already exists or invalid type
    """
    # Get the cuadrilla from database
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    if not cuadrilla:
        raise HTTPException(
            status_code=404,
            detail=f"Cuadrilla with id {cuadrilla_id} not found",
        )

    # Update fields if provided
    if "name" in cuadrilla_update:
        new_name = cuadrilla_update["name"]
        # Check if new name already exists (excluding this cuadrilla)
        existing = (
            db.query(Cuadrilla)
            .filter(Cuadrilla.name == new_name, Cuadrilla.id != cuadrilla_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Cuadrilla with name '{new_name}' already exists",
            )
        cuadrilla.name = new_name

    if "type" in cuadrilla_update:
        try:
            cuadrilla.type = CuadrillaType[cuadrilla_update["type"].upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cuadrilla type: {cuadrilla_update['type']}",
            )

    if "daily_capacity" in cuadrilla_update:
        cuadrilla.daily_capacity = cuadrilla_update["daily_capacity"]

    if "is_active" in cuadrilla_update:
        cuadrilla.is_active = cuadrilla_update["is_active"]

    # Persist changes
    db.commit()
    db.refresh(cuadrilla)

    return cuadrilla


@router.get("/{cuadrilla_id}/centroid", response_model=dict)
async def get_cuadrilla_centroid(
    cuadrilla_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Get cuadrilla's current centroid position and assigned OT locations.

    The centroid represents the geographic center of the cuadrilla's service area
    based on currently assigned OTs. This is used for proximity-based assignment
    decisions and route optimization.

    Path Parameters:
        - cuadrilla_id: ID of the cuadrilla

    Returns:
        Dictionary containing:
        - centroid: {lat, long} of the cuadrilla's centroid
        - assigned_ots: List of assigned OTs with their coordinates
        - ot_count: Number of assigned OTs
        - current_load: Current load as percentage of capacity

    Raises:
        404: Cuadrilla not found
    """
    # Get the cuadrilla from database
    cuadrilla = db.query(Cuadrilla).filter(Cuadrilla.id == cuadrilla_id).first()
    if not cuadrilla:
        raise HTTPException(
            status_code=404,
            detail=f"Cuadrilla with id {cuadrilla_id} not found",
        )

    # Get centroid position
    centroid_lat, centroid_long = cuadrilla.get_centroid()

    # Get assigned OTs with coordinates
    assigned_ots = [
        {
            "id": ot.id,
            "external_id": ot.external_id,
            "status": ot.status.value,
            "project_type": ot.project_type.value,
            "lat": ot.lat,
            "long": ot.long,
        }
        for ot in cuadrilla.get_assigned_ots()
        if ot.lat is not None and ot.long is not None
    ]

    return {
        "centroid": {
            "lat": centroid_lat,
            "long": centroid_long,
        },
        "assigned_ots": assigned_ots,
        "ot_count": cuadrilla.get_ot_count(),
        "current_load": cuadrilla.get_load_percentage(),
    }


@router.post("/balance", response_model=dict)
async def rebalance_cuadrillas(
    db: Session = Depends(get_db),
) -> dict:
    """
    Trigger Planificación Agent to rebalance OT assignments across all cuadrillas.

    This endpoint invokes the PlanificacionAgent via PEIGraphRunner to:
    1. Analyze current OT assignments and cuadrilla loads
    2. Identify unbalanced or suboptimal assignments
    3. Reassign OTs to optimize geographic clustering and load distribution
    4. Update cuadrilla centroids based on new assignments
    5. Execute the 3-phase planning algorithm:
       - PHASE 1: Balance assignments (1 OT per cuadrilla)
       - PHASE 2: Proximity-based assignment (<10km from centroid)
       - PHASE 3: Recalculate centroids for next day optimization

    Returns:
        Dictionary with rebalancing results:
        - status: Operation status
        - message: Description of rebalancing
        - cuadrillas_rebalanced: Count of cuadrillas affected
        - ots_reassigned: Count of OTs reassigned

    Note:
        This is a fire-and-forget operation. The actual agent execution
        is asynchronous and may continue after the endpoint returns.
    """
    # TODO: Implement PEIGraphRunner integration once agents are created
    # For now, return a placeholder response
    return {
        "status": "rebalance_initiated",
        "message": "Planificación Agent invoked to rebalance assignments",
        "cuadrillas_rebalanced": 0,
        "ots_reassigned": 0,
    }

