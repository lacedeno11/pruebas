"""
Pydantic schemas for agent interaction operations.
Provides request/response models for LangGraph agent communication and chat interface.

This module bridges the frontend UI with LangGraph agent operations, including:
- Chat requests/responses for agent interactions
- Status change requests/responses for drag-and-drop operations
- Agent intent classification and routing
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# ENUMS
# ============================================================================


class AgentIntent(str, Enum):
    """
    Classification of user intents for routing to appropriate agents.
    
    Used by RouterAgent to classify incoming requests and route to specialized agents.
    """

    CREATE_OT = "CREATE_OT"
    """Create new Order of Work (OTSAgent)"""

    PLAN_OTS = "PLAN_OTS"
    """Trigger planning algorithm (PlanificacionAgent)"""

    CHECK_STATUS = "CHECK_STATUS"
    """Query OT or crew status (informational)"""

    MANUAL_ASSIGNMENT = "MANUAL_ASSIGNMENT"
    """Manually assign OT to crew (PlanificacionAgent)"""

    CHANGE_STATUS = "CHANGE_STATUS"
    """Change OT workflow status (RouterAgent + GobernanzaAgent)"""

    CHAT_QUERY = "CHAT_QUERY"
    """General query or chat (all agents via RouterAgent)"""


class AgentName(str, Enum):
    """
    LangGraph agent node names for response attribution.
    
    Identifies which agent processed the request.
    """

    ROUTER = "RouterAgent"
    """Intent classification and routing agent"""

    OTS = "OTSAgent"
    """OT ingestion and coordinate validation agent"""

    PLANIFICACION = "PlanificacionAgent"
    """3-phase planning and crew assignment agent"""

    GOBERNANZA = "GobernanzaAgent"
    """Governance, validation, and business rule enforcement agent"""

    COMUNICACION = "ComunicacionAgent"
    """Notification and communication orchestration agent"""

    SYSTEM = "SystemAgent"
    """System-level operations (scheduler, health checks)"""


# ============================================================================
# CHAT REQUEST/RESPONSE SCHEMAS
# ============================================================================


class AgentChatRequest(BaseModel):
    """
    Request for agent chat/interaction.
    
    Used by POST /api/v1/agents/chat endpoint.
    Sends a message to the RouterAgent which classifies intent and routes to
    appropriate specialized agent(s).
    
    Attributes:
        message: User message or command
        context: Optional context dict with state (current OT, crew, filters, etc.)
        intent: Optional explicit intent (for bypassing router classification)
    
    Example:
        {
            "message": "Assign OT-2024-001234 to Cuadrilla Quito-01",
            "context": {
                "current_ot_id": "550e8400-e29b-41d4-a716-446655440000",
                "filters": {
                    "status": "PREPLANIFICADA"
                }
            },
            "intent": "MANUAL_ASSIGNMENT"
        }
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User message or command",
        example="Plan all unassigned OTs",
    )

    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context dictionary with state information",
        example={
            "current_ot_id": "550e8400-e29b-41d4-a716-446655440000",
            "filters": {"status": "PREPLANIFICADA"},
        },
    )

    intent: Optional[AgentIntent] = Field(
        default=None,
        description="Optional explicit intent (bypasses RouterAgent classification)",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class ActionTaken(BaseModel):
    """
    Single action performed by an agent.
    
    Part of agent response to track what operations were executed.
    
    Attributes:
        action: Action name (CREATE_OT, ASSIGN_OT, VALIDATE_DOCUMENTS, etc.)
        target: Object affected (ot_id, cuadrilla_id, etc.)
        status: Result status (SUCCESS, FAILED, SKIPPED)
        details: Additional action details
    """

    action: str = Field(
        description="Action name",
        example="ASSIGN_OT",
    )

    target: Optional[str] = Field(
        default=None,
        description="Primary object affected by action",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    status: str = Field(
        description="Action result: SUCCESS, FAILED, or SKIPPED",
        example="SUCCESS",
    )

    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional action details",
        example={
            "assigned_distance_km": 5.3,
            "crew_load": "8/10",
        },
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class AgentChatResponse(BaseModel):
    """
    Response from agent chat/interaction.
    
    Returned by POST /api/v1/agents/chat endpoint.
    Contains agent response message, identifying which agent responded,
    actions taken, and success status.
    
    Attributes:
        response: Agent response message (for display to user)
        agent_used: Which agent processed request (RouterAgent, OTSAgent, etc.)
        intent_classified: Intent that was classified/routed
        actions_taken: List of actions executed
        success: Whether operation succeeded
        correlation_id: Request tracing ID for log lookup
        execution_time_ms: Milliseconds to execute
        next_steps: Optional suggestions for follow-up actions
    
    Example success response:
        {
            "response": "Successfully assigned 5 OTs to available crews",
            "agent_used": "PlanificacionAgent",
            "intent_classified": "PLAN_OTS",
            "actions_taken": [
                {
                    "action": "ASSIGN_OT",
                    "target": "OT-001",
                    "status": "SUCCESS",
                    "details": {"distance_km": 5.3}
                },
                {
                    "action": "ASSIGN_OT",
                    "target": "OT-002",
                    "status": "SUCCESS",
                    "details": {"distance_km": 7.8}
                }
            ],
            "success": true,
            "correlation_id": "req-12345",
            "execution_time_ms": 245
        }
    
    Example error response:
        {
            "response": "Failed to plan OTs: No available crews",
            "agent_used": "PlanificacionAgent",
            "intent_classified": "PLAN_OTS",
            "actions_taken": [],
            "success": false,
            "correlation_id": "req-12345",
            "execution_time_ms": 120,
            "error_details": "All crews are at capacity"
        }
    """

    response: str = Field(
        ...,
        description="Agent response message for client display",
        example="Successfully assigned 5 unassigned OTs",
    )

    agent_used: AgentName = Field(
        ...,
        description="Which agent processed this request",
    )

    intent_classified: Optional[AgentIntent] = Field(
        default=None,
        description="Intent that was classified and routed",
    )

    actions_taken: List[ActionTaken] = Field(
        default_factory=list,
        description="List of actions executed by agent",
    )

    success: bool = Field(
        ...,
        description="Whether operation was successful",
    )

    correlation_id: str = Field(
        ...,
        description="Request correlation ID for tracing",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    execution_time_ms: int = Field(
        ...,
        description="Milliseconds to execute request",
        example=245,
    )

    next_steps: Optional[List[str]] = Field(
        default=None,
        description="Suggested follow-up actions",
        example=["View assignments on map", "Check crew capacity"],
    )

    error_details: Optional[str] = Field(
        default=None,
        description="Error message if operation failed",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# LOG RETRIEVAL SCHEMAS
# ============================================================================


class AgentLogFilters(BaseModel):
    """
    Query filters for retrieving agent logs.
    
    Used by GET /api/v1/agents/logs endpoint.
    
    Attributes:
        agent_name: Filter by agent (Router, OTS, Planificacion, Gobernanza, Comunicacion)
        ot_id: Filter by OT affected
        resultado: Filter by result (SUCCESS, FAILED, SKIPPED)
        correlation_id: Filter by request trace ID
        from_timestamp: Start of date range
        to_timestamp: End of date range
        page: Page number (1-indexed)
        page_size: Items per page
    """

    agent_name: Optional[AgentName] = Field(
        default=None,
        description="Filter by agent name",
    )

    ot_id: Optional[str] = Field(
        default=None,
        description="Filter by affected OT",
    )

    resultado: Optional[str] = Field(
        default=None,
        description="Filter by result: SUCCESS, FAILED, or SKIPPED",
    )

    correlation_id: Optional[str] = Field(
        default=None,
        description="Filter by request correlation ID for tracing",
    )

    from_timestamp: Optional[datetime] = Field(
        default=None,
        description="Start of date range for log search",
    )

    to_timestamp: Optional[datetime] = Field(
        default=None,
        description="End of date range for log search",
    )

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)",
    )

    page_size: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Items per page (max 500)",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# HEALTH/STATUS SCHEMAS
# ============================================================================


class AgentNodeStatus(BaseModel):
    """
    Status of a single agent node in the graph.
    
    Attributes:
        node_name: Agent node name
        status: operational/degraded/offline
        last_execution: Timestamp of last execution
        success_count: Total successful operations
        failure_count: Total failed operations
        average_duration_ms: Average execution time
    """

    node_name: AgentName = Field(description="Agent node identifier")
    status: str = Field(description="operational, degraded, or offline")
    last_execution: Optional[datetime] = Field(default=None)
    success_count: int = Field(default=0)
    failure_count: int = Field(default=0)
    average_duration_ms: float = Field(default=0.0)

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class AgentGraphHealthResponse(BaseModel):
    """
    Health status of entire LangGraph agent system.
    
    Used by GET /api/v1/agents/health endpoint.
    
    Attributes:
        healthy: Overall system health
        graph_status: Graph construction status
        nodes: Status of each agent node
        last_check: Timestamp of last health check
    """

    healthy: bool = Field(description="Overall system health status")
    graph_status: str = Field(description="Graph construction status")
    nodes: List[AgentNodeStatus] = Field(description="Status of each agent node")
    last_check: datetime = Field(description="Timestamp of last health check")
    message: Optional[str] = Field(default=None, description="Health status message")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# AGENT INTENT ROUTING SCHEMAS
# ============================================================================


class IntentClassificationResponse(BaseModel):
    """
    Response from intent classification (internal use).
    
    Used internally by RouterAgent to classify user intent.
    
    Attributes:
        intent: Classified intent
        confidence: Confidence score (0-1)
        alternative_intents: Other possible intents
        reasoning: Explanation of classification
    """

    intent: AgentIntent = Field(description="Classified intent")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for classification",
    )
    alternative_intents: Optional[List[AgentIntent]] = Field(
        default=None,
        description="Other possible intents if low confidence",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of why this intent was chosen",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# BATCH OPERATION SCHEMAS (for future use)
# ============================================================================


class BatchAgentRequest(BaseModel):
    """
    Request for batch operations across multiple OTs.
    
    Future enhancement for bulk operations through agents.
    
    Attributes:
        operation: Bulk operation (PLAN_ALL, REASSIGN_ALL, VALIDATE_ALL)
        filter_criteria: Optional filters to select OTs
        dry_run: If True, simulate without persisting
    """

    operation: str = Field(
        description="Bulk operation name",
        example="PLAN_ALL",
    )

    filter_criteria: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filters to select OTs for operation",
        example={"status": "PREPLANIFICADA", "project_type": "PUBLICO"},
    )

    dry_run: bool = Field(
        default=False,
        description="If True, simulate without persisting",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class BatchAgentResponse(BaseModel):
    """
    Response from batch agent operation.
    
    Attributes:
        operation: Operation that was performed
        total_processed: Total OTs processed
        successful: Number of successful operations
        failed: Number of failed operations
        skipped: Number of skipped operations
        details: Per-OT operation results
        summary: Overall summary message
    """

    operation: str = Field(description="Operation that was performed")
    total_processed: int = Field(description="Total OTs processed")
    successful: int = Field(description="Successful operations")
    failed: int = Field(description="Failed operations")
    skipped: int = Field(description="Skipped operations")
    details: List[Dict[str, Any]] = Field(description="Per-OT results")
    summary: str = Field(description="Operation summary")

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# STATUS CHANGE SCHEMAS (moved here from ot.py for agent operations)
# ============================================================================


class StatusChangeRequest(BaseModel):
    """
    Request body for OT status change operation.
    
    Used by POST /api/v1/ots/{ot_id}/change-status endpoint.
    Triggers RouterAgent -> GobernanzaAgent validation chain.
    
    For DETENIDA status, a reason is required from predefined ontology:
    - FALTA_MATERIAL: Missing materials/equipment
    - CLIENTE_AUSENTE: Customer not available
    - CONDICIONES_CLIMATICAS: Weather conditions
    - PERMISOS_PENDIENTES: Awaiting permits
    - OTRO: Other reason (with description)
    
    Attributes:
        new_status: Target OT status
        reason: Required reason if moving to DETENIDA
        notes: Optional additional notes
    
    Example:
        {
            "new_status": "DETENIDA",
            "reason": "FALTA_MATERIAL",
            "notes": "Waiting for fiber optic cable delivery"
        }
    """

    new_status: str = Field(
        ...,
        description="Target OT status",
        example="DETENIDA",
    )

    reason: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Reason for status change (required if moving to DETENIDA)",
        example="FALTA_MATERIAL",
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional additional notes/context",
        example="Waiting for fiber optic cable delivery scheduled for tomorrow",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class StatusChangeResponse(BaseModel):
    """
    Response for OT status change operation.
    
    Returned by POST /api/v1/ots/{ot_id}/change-status endpoint.
    Includes success status, message, rollback flag for UI, and validation details.
    
    The rollback flag indicates whether the frontend should revert the visual
    drag-and-drop change. This supports optimistic UI updates with error recovery.
    
    Attributes:
        success: Whether status change was successful
        message: User-friendly result message
        rollback: If True, client should revert visual change (operation failed)
        validation_details: Details about validation failures (if any)
        previous_status: Status before change (for UI display)
        new_status: Status after change (for UI display)
        executed_by: Which agent executed the change
        timestamp: When change was executed
    
    Example success response:
        {
            "success": true,
            "message": "OT status changed to DETENIDA",
            "rollback": false,
            "validation_details": {},
            "previous_status": "ASIGNADO_TAREA",
            "new_status": "DETENIDA",
            "executed_by": "GobernanzaAgent",
            "timestamp": "2024-02-13T16:45:30.654321"
        }
    
    Example validation failure:
        {
            "success": false,
            "message": "Cannot finalize PUBLIC project without 29 documents",
            "rollback": true,
            "validation_details": {
                "required_documents": 29,
                "completed_documents": 25,
                "missing_documents": ["Document Type A", "Document Type B"]
            },
            "previous_status": "DETENIDA",
            "new_status": "FINALIZADA",
            "executed_by": "GobernanzaAgent",
            "timestamp": "2024-02-13T16:45:30.654321"
        }
    """

    success: bool = Field(
        ...,
        description="Whether status change was successful",
    )

    message: str = Field(
        ...,
        description="User-friendly message about operation result",
        example="OT status changed to DETENIDA",
    )

    rollback: bool = Field(
        ...,
        description="If True, client should revert visual change (operation failed)",
    )

    validation_details: dict = Field(
        default_factory=dict,
        description="Details about validation failures (if applicable)",
    )

    previous_status: Optional[str] = Field(
        default=None,
        description="OT status before change",
    )

    new_status: Optional[str] = Field(
        default=None,
        description="OT status after change",
    )

    executed_by: Optional[str] = Field(
        default=None,
        description="Agent that executed the change",
    )

    timestamp: Optional[datetime] = Field(
        default=None,
        description="When change was executed",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


# ============================================================================
# MANUAL ASSIGNMENT SCHEMAS
# ============================================================================


class ManualAssignmentRequest(BaseModel):
    """
    Request for manual OT assignment to crew.
    
    Used by POST /api/v1/planning/reassign endpoint.
    Bypasses normal planning algorithm and forces assignment.
    
    Attributes:
        ot_id: OT to assign
        cuadrilla_id: Target crew
        force: If True, override capacity constraints
        reason: Why this manual assignment is needed
    """

    ot_id: str = Field(
        ...,
        description="OT to assign",
        example="550e8400-e29b-41d4-a716-446655440000",
    )

    cuadrilla_id: str = Field(
        ...,
        description="Target crew",
        example="f47ac10b-58cc-4372-a567-0e02b2c3d479",
    )

    force: bool = Field(
        default=False,
        description="If True, override capacity and distance constraints",
    )

    reason: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Reason for manual assignment",
    )

    class Config:
        """Pydantic configuration"""
        from_attributes = True


class ManualAssignmentResponse(BaseModel):
    """
    Response for manual assignment operation.
    
    Attributes:
        success: Whether assignment succeeded
        message: Result message
        assignment_id: ID of created assignment record
        distance_from_centroid_km: Distance from crew centroid
        affected_ot: Assigned OT details
        assigned_cuadrilla: Assigned crew details
        validation_warnings: Any warnings from validation
    """

    success: bool = Field(description="Whether assignment succeeded")
    message: str = Field(description="Result message")
    assignment_id: Optional[str] = Field(default=None)
    distance_from_centroid_km: Optional[float] = Field(default=None)
    affected_ot: Optional[Dict[str, Any]] = Field(default=None)
    assigned_cuadrilla: Optional[Dict[str, Any]] = Field(default=None)
    validation_warnings: List[str] = Field(default_factory=list)

    class Config:
        """Pydantic configuration"""
        from_attributes = True

