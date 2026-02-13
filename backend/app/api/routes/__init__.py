"""
API routes aggregation module.

This module imports and aggregates all API route routers, providing a single
entry point for including all routes in the FastAPI application.

Routers included:
- OTs: Work order management endpoints
- Cuadrillas: Work crew management endpoints
- Planning: Planning and scheduling operations
- Agents: Agent interaction and logging endpoints
- Governance: Governance monitoring and compliance endpoints
- Drag & Drop: Real-time drag-drop validation endpoints
"""

import logging
from typing import Optional

from fastapi import FastAPI

# Import all routers
from backend.app.api.routes.ots import router as ots_router
from backend.app.api.routes.cuadrillas import router as cuadrillas_router
from backend.app.api.routes.planning import router as planning_router
from backend.app.api.routes.agents import router as agents_router
from backend.app.api.routes.governance import router as governance_router
from backend.app.api.routes.drag_drop import router as drag_drop_router

logger = logging.getLogger(__name__)


def include_routers(app: FastAPI, prefix: str = "/api") -> None:
    """
    Include all API routers in the FastAPI application.
    
    This function registers all route modules with the FastAPI app,
    organizing them under the /api prefix with appropriate tags for
    OpenAPI documentation.
    
    Args:
        app: FastAPI application instance
        prefix: URL prefix for all routes (default: "/api")
    
    Routers registered:
    - /api/ots: OT management (external_id, status, project_type, assignments)
    - /api/cuadrillas: Cuadrilla management (name, type, capacity, workload)
    - /api/planning: Planning operations (auto-plan, manual assign, optimize)
    - /api/agents: Agent operations (chat, logs, direct execution)
    - /api/governance: Governance monitoring (checks, alerts, documents, auto-cancel)
    - /api/drag-drop: Drag-drop validation (validate, commit)
    
    Example:
        ```python
        from fastapi import FastAPI
        from backend.app.api.routes import include_routers
        
        app = FastAPI()
        include_routers(app)
        ```
    """
    try:
        # Include OTs router
        app.include_router(
            ots_router,
            prefix=prefix,
            tags=["OTs"],
        )
        logger.info(f"Included OTs router at {prefix}/ots")
        
        # Include Cuadrillas router
        app.include_router(
            cuadrillas_router,
            prefix=prefix,
            tags=["Cuadrillas"],
        )
        logger.info(f"Included Cuadrillas router at {prefix}/cuadrillas")
        
        # Include Planning router
        app.include_router(
            planning_router,
            prefix=prefix,
            tags=["Planning"],
        )
        logger.info(f"Included Planning router at {prefix}/planning")
        
        # Include Agents router
        app.include_router(
            agents_router,
            prefix=prefix,
            tags=["Agents"],
        )
        logger.info(f"Included Agents router at {prefix}/agents")
        
        # Include Governance router
        app.include_router(
            governance_router,
            prefix=prefix,
            tags=["Governance"],
        )
        logger.info(f"Included Governance router at {prefix}/governance")
        
        # Include Drag-Drop router
        app.include_router(
            drag_drop_router,
            prefix=prefix,
            tags=["Drag & Drop"],
        )
        logger.info(f"Included Drag-Drop router at {prefix}/drag-drop")
        
        logger.info("All API routers included successfully")
        
    except Exception as e:
        logger.error(f"Error including routers: {str(e)}", exc_info=True)
        raise


# Export routers for direct access if needed
__all__ = [
    "include_routers",
    "ots_router",
    "cuadrillas_router",
    "planning_router",
    "agents_router",
    "governance_router",
    "drag_drop_router",
]

