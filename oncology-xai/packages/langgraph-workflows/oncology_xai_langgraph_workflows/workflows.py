# DERCAS-ONCO-XAI V1 - LangGraph Workflow Components
# Base workflow classes and utilities for creating LangGraph workflows

from typing import Optional, Dict, Any, List, Callable, Union, Type
from abc import ABC, abstractmethod
from datetime import datetime
import asyncio
import logging
from langgraph import StateGraph, END
from langgraph.graph import Graph
from pydantic import BaseModel

from .state import BaseGraphState
from .tools import BaseTool

logger = logging.getLogger(__name__)


class WorkflowNode(BaseModel):
    """Represents a node in a workflow graph."""
    
    name: str
    description: str
    function: Optional[Callable] = None
    tools: List[BaseTool] = []
    timeout_seconds: int = 300
    retry_count: int = 3
    
    class Config:
        arbitrary_types_allowed = True


class WorkflowEdge(BaseModel):
    """Represents an edge in a workflow graph."""
    
    from_node: str
    to_node: str
    condition: Optional[Callable] = None
    
    class Config:
        arbitrary_types_allowed = True


class ConditionalEdge(BaseModel):
    """Represents a conditional edge with multiple possible destinations."""
    
    from_node: str
    condition_function: Callable
    condition_map: Dict[str, str]  # condition_result -> target_node
    
    class Config:
        arbitrary_types_allowed = True


class BaseWorkflow(ABC):
    """
    Base class for all LangGraph workflows in the oncology platform.
    
    This class provides:
    - Common workflow structure and lifecycle management
    - Error handling and retry logic
    - Progress tracking and metrics
    - Tool integration
    - State management
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        state_class: Type[BaseGraphState] = BaseGraphState
    ):
        self.name = name
        self.description = description
        self.state_class = state_class
        self.graph: Optional[StateGraph] = None
        self.nodes: List[WorkflowNode] = []
        self.edges: List[WorkflowEdge] = []
        self.conditional_edges: List[ConditionalEdge] = []
        self.tools: Dict[str, BaseTool] = {}
        
        logger.info(f"Initialized workflow: {name}")
    
    @abstractmethod
    def define_nodes(self) -> List[WorkflowNode]:
        """Define the nodes for this workflow."""
        pass
    
    @abstractmethod
    def define_edges(self) -> List[Union[WorkflowEdge, ConditionalEdge]]:
        """Define the edges for this workflow."""
        pass
    
    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the workflow."""
        self.tools[tool.name] = tool
        logger.debug(f"Added tool {tool.name} to workflow {self.name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(tool_name)
    
    def build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph."""
        if self.graph is not None:
            return self.graph
        
        # Create state graph
        self.graph = StateGraph(self.state_class)
        
        # Define nodes
        self.nodes = self.define_nodes()
        for node in self.nodes:
            self.graph.add_node(node.name, self._create_node_function(node))
        
        # Define edges
        edges = self.define_edges()
        for edge in edges:
            if isinstance(edge, WorkflowEdge):
                if edge.condition:
                    # This is actually a conditional edge
                    self.graph.add_conditional_edges(
                        edge.from_node,
                        edge.condition,
                        {True: edge.to_node, False: END}
                    )
                else:
                    self.graph.add_edge(edge.from_node, edge.to_node)
            elif isinstance(edge, ConditionalEdge):
                self.graph.add_conditional_edges(
                    edge.from_node,
                    edge.condition_function,
                    edge.condition_map
                )
        
        # Set entry point (first node)
        if self.nodes:
            self.graph.set_entry_point(self.nodes[0].name)
        
        logger.info(f"Built graph for workflow: {self.name}")
        return self.graph
    
    def _create_node_function(self, node: WorkflowNode) -> Callable:
        """Create a function for a workflow node."""
        async def node_function(state: BaseGraphState) -> BaseGraphState:
            logger.info(f"Executing node: {node.name}")
            
            try:
                # Update progress
                state.update_progress(0.0, node.name)
                
                # Execute node function if provided
                if node.function:
                    if asyncio.iscoroutinefunction(node.function):
                        result = await node.function(state, self.tools)
                    else:
                        result = node.function(state, self.tools)
                    
                    # Update state with result if returned
                    if isinstance(result, BaseGraphState):
                        state = result
                    elif isinstance(result, dict):
                        state.workflow_data.update(result)
                
                # Mark node as completed
                state.update_progress(1.0, node.name)
                logger.info(f"Completed node: {node.name}")
                
                return state
                
            except Exception as e:
                logger.error(f"Error in node {node.name}: {e}")
                state.add_error(
                    error_code=f"{node.name.upper()}_ERROR",
                    error_message=str(e),
                    node=node.name
                )
                
                # Decide whether to retry or fail
                if state.execution.retry_count < node.retry_count:
                    state.execution.retry_count += 1
                    logger.info(f"Retrying node {node.name} (attempt {state.execution.retry_count})")
                    return await node_function(state)  # Retry
                else:
                    state.fail_workflow(f"{node.name.upper()}_ERROR", str(e))
                    return state
        
        return node_function
    
    async def execute(self, initial_state: BaseGraphState) -> BaseGraphState:
        """Execute the workflow with the given initial state."""
        logger.info(f"Starting workflow execution: {self.name}")
        
        # Build graph if not already built
        if self.graph is None:
            self.build_graph()
        
        # Start workflow execution
        initial_state.start_workflow(self.nodes[0].name if self.nodes else None)
        
        try:
            # Compile and run the graph
            compiled_graph = self.graph.compile()
            final_state = await compiled_graph.ainvoke(initial_state)
            
            # Mark as completed if not already failed
            if final_state.execution.status == "RUNNING":
                final_state.complete_workflow()
            
            logger.info(f"Completed workflow execution: {self.name}")
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {self.name} - {e}")
            initial_state.fail_workflow("WORKFLOW_EXECUTION_ERROR", str(e))
            return initial_state
    
    def get_schema(self) -> Dict[str, Any]:
        """Get workflow schema for documentation."""
        return {
            "name": self.name,
            "description": self.description,
            "nodes": [
                {
                    "name": node.name,
                    "description": node.description,
                    "tools": [tool.name for tool in node.tools]
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "from": edge.from_node,
                    "to": edge.to_node,
                    "conditional": edge.condition is not None
                }
                for edge in self.edges
            ]
        }


class ImageAnalysisWorkflow(BaseWorkflow):
    """
    Image analysis workflow for processing histopathological images.
    
    Nodes: ValidateInput → LoadImage → RunPatternModel → RunMutationModel → 
           GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize
    """
    
    def __init__(self):
        from .state import ImageAnalysisState
        super().__init__(
            name="ImageAnalysisWorkflow",
            description="Workflow for analyzing histopathological images",
            state_class=ImageAnalysisState
        )
    
    def define_nodes(self) -> List[WorkflowNode]:
        """Define nodes for image analysis workflow."""
        return [
            WorkflowNode(
                name="validate_input",
                description="Validate input parameters and image availability",
                function=self._validate_input
            ),
            WorkflowNode(
                name="load_image",
                description="Load and preprocess the image",
                function=self._load_image
            ),
            WorkflowNode(
                name="run_pattern_model",
                description="Run pattern detection model",
                function=self._run_pattern_model
            ),
            WorkflowNode(
                name="run_mutation_model",
                description="Run genetic mutation prediction model",
                function=self._run_mutation_model
            ),
            WorkflowNode(
                name="generate_xai",
                description="Generate explainability artifacts",
                function=self._generate_xai
            ),
            WorkflowNode(
                name="assemble_result_bundle",
                description="Assemble results into a bundle",
                function=self._assemble_result_bundle
            ),
            WorkflowNode(
                name="policy_check",
                description="Check policies and guardrails",
                function=self._policy_check
            ),
            WorkflowNode(
                name="persist_and_audit",
                description="Persist results and create audit trail",
                function=self._persist_and_audit
            ),
            WorkflowNode(
                name="finalize",
                description="Finalize workflow execution",
                function=self._finalize
            )
        ]
    
    def define_edges(self) -> List[Union[WorkflowEdge, ConditionalEdge]]:
        """Define edges for image analysis workflow."""
        return [
            WorkflowEdge(from_node="validate_input", to_node="load_image"),
            WorkflowEdge(from_node="load_image", to_node="run_pattern_model"),
            WorkflowEdge(from_node="run_pattern_model", to_node="run_mutation_model"),
            WorkflowEdge(from_node="run_mutation_model", to_node="generate_xai"),
            WorkflowEdge(from_node="generate_xai", to_node="assemble_result_bundle"),
            WorkflowEdge(from_node="assemble_result_bundle", to_node="policy_check"),
            ConditionalEdge(
                from_node="policy_check",
                condition_function=self._check_hitl_required,
                condition_map={
                    "continue": "persist_and_audit",
                    "hitl_required": END,  # Would trigger HITL process
                    "failed": END
                }
            ),
            WorkflowEdge(from_node="persist_and_audit", to_node="finalize"),
            WorkflowEdge(from_node="finalize", to_node=END)
        ]
    
    async def _validate_input(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Validate input parameters."""
        if not state.inputs.image_id and not state.inputs.image_uri:
            raise ValueError("No image ID or URI provided")
        
        state.workflow_data["validation_passed"] = True
        return state
    
    async def _load_image(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Load and preprocess image."""
        storage_client = tools.get("storage_client")
        if storage_client and state.inputs.image_uri:
            # Download image for processing
            result = await storage_client.execute(
                operation="download",
                object_key=state.inputs.image_uri,
                local_path="/tmp/image.png"
            )
            state.workflow_data["image_loaded"] = True
            state.workflow_data["local_image_path"] = result.get("local_path")
        
        return state
    
    async def _run_pattern_model(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Run pattern detection model."""
        model_client = tools.get("model_client")
        if model_client:
            result = await model_client.execute(
                model_name="lung_patterns_v3",
                image_uri=state.inputs.image_uri,
                parameters=state.inputs.parameters
            )
            
            # Add pattern results to output
            for pattern_data in result.get("patterns", []):
                state.outputs.add_pattern_result(**pattern_data)
            
            state.workflow_data["pattern_results"] = result
        
        return state
    
    async def _run_mutation_model(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Run genetic mutation prediction model."""
        model_client = tools.get("model_client")
        if model_client:
            result = await model_client.execute(
                model_name="lung_mutations_v2",
                image_uri=state.inputs.image_uri,
                parameters=state.inputs.parameters
            )
            
            # Add genetic results to output
            for mutation_data in result.get("mutations", []):
                state.outputs.add_genetic_result(**mutation_data)
            
            state.workflow_data["mutation_results"] = result
        
        return state
    
    async def _generate_xai(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Generate explainability artifacts."""
        # Mock XAI generation
        xai_artifacts = [
            {"type": "overlay", "pattern": "acinar", "uri": "s3://bucket/overlay1.png"},
            {"type": "heatmap", "pattern": "acinar", "uri": "s3://bucket/heatmap1.png"}
        ]
        
        for artifact in xai_artifacts:
            state.outputs.xai_artifacts.append(artifact["uri"])
            state.outputs.add_artifact(
                name=f"{artifact['type']}_{artifact['pattern']}",
                uri=artifact["uri"]
            )
        
        state.workflow_data["xai_generated"] = True
        return state
    
    async def _assemble_result_bundle(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Assemble results into a bundle."""
        # Create result bundle ID
        import uuid
        result_bundle_id = str(uuid.uuid4())
        state.outputs.result_bundle_id = result_bundle_id
        
        # Assemble summary
        summary = {
            "patterns": len(state.outputs.pattern_outputs),
            "mutations": len(state.outputs.genetic_outputs),
            "xai_artifacts": len(state.outputs.xai_artifacts),
            "processing_time": (datetime.utcnow() - state.execution.started_at).total_seconds() if state.execution.started_at else 0
        }
        
        state.outputs.metadata["summary"] = summary
        state.workflow_data["result_bundle_assembled"] = True
        return state
    
    async def _policy_check(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Check policies and guardrails."""
        # Check confidence thresholds
        scores = {}
        for pattern_result in state.outputs.pattern_outputs:
            scores[pattern_result["pattern"]] = pattern_result["score"]
        
        for genetic_result in state.outputs.genetic_outputs:
            scores[genetic_result["mutation"]] = genetic_result["score"]
        
        # Check if HITL is required
        hitl_required = state.should_trigger_hitl(scores)
        state.workflow_data["hitl_required"] = hitl_required
        state.workflow_data["policy_check_passed"] = not hitl_required
        
        return state
    
    async def _persist_and_audit(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Persist results and create audit trail."""
        # Mock persistence
        state.workflow_data["results_persisted"] = True
        state.workflow_data["audit_created"] = True
        return state
    
    async def _finalize(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Finalize workflow execution."""
        state.workflow_data["finalized"] = True
        return state
    
    def _check_hitl_required(self, state: BaseGraphState) -> str:
        """Check if human-in-the-loop is required."""
        if state.workflow_data.get("hitl_required", False):
            return "hitl_required"
        elif state.workflow_data.get("policy_check_passed", False):
            return "continue"
        else:
            return "failed"


class EHRAnalysisWorkflow(BaseWorkflow):
    """
    EHR analysis workflow for processing electronic health records.
    
    Nodes: NormalizeEHR → ExtractEntities → LookupCandidates → 
           Disambiguate → BuildEvidencePack → PersistEntitiesMappings → Finalize
    """
    
    def __init__(self):
        from .state import EHRAnalysisState
        super().__init__(
            name="EHRAnalysisWorkflow",
            description="Workflow for analyzing electronic health records",
            state_class=EHRAnalysisState
        )
    
    def define_nodes(self) -> List[WorkflowNode]:
        """Define nodes for EHR analysis workflow."""
        return [
            WorkflowNode(
                name="normalize_ehr",
                description="Normalize and clean EHR text",
                function=self._normalize_ehr
            ),
            WorkflowNode(
                name="extract_entities",
                description="Extract clinical entities from text",
                function=self._extract_entities
            ),
            WorkflowNode(
                name="lookup_candidates",
                description="Look up ontology candidates for entities",
                function=self._lookup_candidates
            ),
            WorkflowNode(
                name="disambiguate",
                description="Disambiguate entity mappings",
                function=self._disambiguate
            ),
            WorkflowNode(
                name="build_evidence_pack",
                description="Build evidence pack for mappings",
                function=self._build_evidence_pack
            ),
            WorkflowNode(
                name="persist_entities_mappings",
                description="Persist entities and mappings",
                function=self._persist_entities_mappings
            ),
            WorkflowNode(
                name="finalize",
                description="Finalize workflow execution",
                function=self._finalize
            )
        ]
    
    def define_edges(self) -> List[Union[WorkflowEdge, ConditionalEdge]]:
        """Define edges for EHR analysis workflow."""
        return [
            WorkflowEdge(from_node="normalize_ehr", to_node="extract_entities"),
            WorkflowEdge(from_node="extract_entities", to_node="lookup_candidates"),
            WorkflowEdge(from_node="lookup_candidates", to_node="disambiguate"),
            WorkflowEdge(from_node="disambiguate", to_node="build_evidence_pack"),
            WorkflowEdge(from_node="build_evidence_pack", to_node="persist_entities_mappings"),
            WorkflowEdge(from_node="persist_entities_mappings", to_node="finalize"),
            WorkflowEdge(from_node="finalize", to_node=END)
        ]
    
    async def _normalize_ehr(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Normalize EHR text."""
        # Mock normalization
        state.workflow_data["normalized_text"] = state.inputs.ehr_text
        state.workflow_data["normalization_completed"] = True
        return state
    
    async def _extract_entities(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Extract entities from EHR text."""
        llm_client = tools.get("llm_client")
        if llm_client:
            result = await llm_client.execute(
                prompt=f"Extract clinical entities from this text: {state.inputs.ehr_text}",
                max_tokens=500
            )
            
            # Mock entity extraction results
            entities = [
                {"text": "lung adenocarcinoma", "type": "DIAGNOSIS", "confidence": 0.95, "start": 0, "end": 18},
                {"text": "EGFR positive", "type": "MUTATION", "confidence": 0.87, "start": 50, "end": 63}
            ]
            
            for entity in entities:
                state.outputs.add_ehr_entity(**entity)
            
            state.workflow_data["entities_extracted"] = True
        
        return state
    
    async def _lookup_candidates(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Look up ontology candidates."""
        sparql_client = tools.get("sparql_client")
        if sparql_client:
            # Mock SPARQL lookup
            for entity in state.outputs.ehr_entities:
                query = f"SELECT ?concept WHERE {{ ?concept rdfs:label '{entity['text']}' }}"
                result = await sparql_client.execute(operation="query", query=query)
                
                # Mock mapping results
                state.outputs.add_ehr_mapping(
                    entity_text=entity["text"],
                    ontology="NCIt",
                    iri="http://purl.obolibrary.org/obo/NCIT_C3512",
                    confidence=0.9
                )
        
        state.workflow_data["candidates_found"] = True
        return state
    
    async def _disambiguate(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Disambiguate entity mappings."""
        state.workflow_data["disambiguation_completed"] = True
        return state
    
    async def _build_evidence_pack(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Build evidence pack."""
        state.workflow_data["evidence_pack_built"] = True
        return state
    
    async def _persist_entities_mappings(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Persist entities and mappings."""
        state.workflow_data["entities_persisted"] = True
        return state
    
    async def _finalize(self, state: BaseGraphState, tools: Dict[str, BaseTool]) -> BaseGraphState:
        """Finalize workflow."""
        state.workflow_data["finalized"] = True
        return state


def create_workflow_graph(workflow: BaseWorkflow) -> StateGraph:
    """Create a LangGraph StateGraph from a workflow definition."""
    return workflow.build_graph()


# Workflow factory functions

def create_image_analysis_workflow() -> ImageAnalysisWorkflow:
    """Create an image analysis workflow."""
    return ImageAnalysisWorkflow()


def create_ehr_analysis_workflow() -> EHRAnalysisWorkflow:
    """Create an EHR analysis workflow."""
    return EHRAnalysisWorkflow()


# Workflow registry

WORKFLOW_REGISTRY = {
    "image_analysis": ImageAnalysisWorkflow,
    "ehr_analysis": EHRAnalysisWorkflow,
}


def get_workflow(workflow_name: str) -> BaseWorkflow:
    """Get a workflow by name."""
    workflow_class = WORKFLOW_REGISTRY.get(workflow_name)
    if not workflow_class:
        raise ValueError(f"Unknown workflow: {workflow_name}")
    
    return workflow_class()


def list_workflows() -> List[str]:
    """List available workflows."""
    return list(WORKFLOW_REGISTRY.keys())
