"""Graph Assembler LangGraph workflow.

Nodes: FetchCaseFindings → QuerySubgraph → FuseAnnotateProvenance →
       BuildLayout → PersistSnapshot → Finalize
"""

from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph, END

from langgraph_workflows.state import GraphState, update_execution


async def fetch_case_findings(state: GraphState) -> GraphState:
    """Fetch case findings from database."""
    state = update_execution(state, status="running", progress=0.0, current_node="fetch_case_findings")

    context = state.get("context", {})
    case_id = context.get("case_id")

    if not case_id:
        state = update_execution(
            state,
            error={"code": "VALIDATION_ERROR", "message": "case_id required"},
        )
        state["execution"]["status"] = "failed"
        return state

    # Mock findings - in real implementation would query database
    intermediate = state.get("_intermediate_results", {})
    intermediate["findings"] = {
        "patterns": [
            {"pattern": "lepidic", "score": 0.75, "detected": True},
            {"pattern": "acinar", "score": 0.82, "detected": True},
        ],
        "mutations": [
            {"mutation": "EGFR", "status": "POS", "score": 0.68},
            {"mutation": "KRAS", "status": "NEG", "score": 0.25},
        ],
        "ehr_entities": [
            {"text": "lung adenocarcinoma", "type": "DIAGNOSIS"},
        ],
        "mappings": [
            {"iri": "http://purl.obolibrary.org/obo/NCIT_C3512", "label": "Lung Adenocarcinoma"},
        ],
    }
    state["_intermediate_results"] = intermediate

    return state


async def query_subgraph(state: GraphState) -> GraphState:
    """Query relevant subgraph from triple store."""
    state = update_execution(state, progress=0.25, current_node="query_subgraph")

    if state["execution"]["status"] == "failed":
        return state

    context = state.get("context", {})
    case_id = context.get("case_id")

    # Mock subgraph nodes
    intermediate = state.get("_intermediate_results", {})

    nodes = [
        {
            "id": f"case_{case_id}",
            "label": f"Case {case_id}",
            "type": "Case",
            "iri": f"urn:oncology:case:{case_id}",
            "source": "internal",
        },
        {
            "id": "ncit_c3512",
            "label": "Lung Adenocarcinoma",
            "type": "Diagnosis",
            "iri": "http://purl.obolibrary.org/obo/NCIT_C3512",
            "source": "ontology",
        },
        {
            "id": "pattern_lepidic",
            "label": "Lepidic Pattern",
            "type": "Pattern",
            "iri": "http://purl.obolibrary.org/obo/NCIT_C136486",
            "source": "image",
        },
        {
            "id": "pattern_acinar",
            "label": "Acinar Pattern",
            "type": "Pattern",
            "iri": "http://purl.obolibrary.org/obo/NCIT_C136487",
            "source": "image",
        },
        {
            "id": "mutation_egfr",
            "label": "EGFR Mutation",
            "type": "Mutation",
            "iri": "http://purl.obolibrary.org/obo/NCIT_C51744",
            "source": "image",
        },
    ]

    edges = [
        {"source": f"case_{case_id}", "target": "ncit_c3512", "label": "hasDiagnosis", "type": "asserted"},
        {"source": f"case_{case_id}", "target": "pattern_lepidic", "label": "hasPattern", "type": "asserted"},
        {"source": f"case_{case_id}", "target": "pattern_acinar", "label": "hasPattern", "type": "asserted"},
        {"source": f"case_{case_id}", "target": "mutation_egfr", "label": "hasMutation", "type": "asserted"},
        {"source": "ncit_c3512", "target": "pattern_lepidic", "label": "typicalPattern", "type": "inferred"},
        {"source": "ncit_c3512", "target": "mutation_egfr", "label": "associatedMutation", "type": "inferred"},
    ]

    intermediate["raw_nodes"] = nodes
    intermediate["raw_edges"] = edges
    state["_intermediate_results"] = intermediate

    return state


async def fuse_annotate_provenance(state: GraphState) -> GraphState:
    """Fuse graphs and annotate with provenance."""
    state = update_execution(state, progress=0.5, current_node="fuse_annotate_provenance")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    nodes = intermediate.get("raw_nodes", [])
    edges = intermediate.get("raw_edges", [])

    # Add provenance to nodes
    for node in nodes:
        node["properties"] = {
            "source_type": node.get("source", "unknown"),
            "ontology_version": "NCIt_23.10" if "ncit" in node.get("id", "").lower() else None,
        }

    # Add provenance to edges
    provenance = []
    for edge in edges:
        prov_entry = {
            "edge": f"{edge['source']} -> {edge['target']}",
            "type": edge["type"],
            "source": "image_analysis" if edge["type"] == "asserted" else "reasoner",
        }
        provenance.append(prov_entry)

    intermediate["provenance"] = provenance
    state["_intermediate_results"] = intermediate

    return state


async def build_layout(state: GraphState) -> GraphState:
    """Build layout model for visualization."""
    state = update_execution(state, progress=0.75, current_node="build_layout")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    nodes = intermediate.get("raw_nodes", [])

    # Simple force-directed layout mock (just assign positions)
    layout = {}
    for i, node in enumerate(nodes):
        angle = (i / len(nodes)) * 6.28  # 2*pi
        import math
        layout[node["id"]] = {
            "x": 300 + 200 * math.cos(angle),
            "y": 300 + 200 * math.sin(angle),
        }

    intermediate["layout"] = layout
    state["_intermediate_results"] = intermediate

    return state


async def persist_snapshot(state: GraphState) -> GraphState:
    """Persist graph snapshot."""
    state = update_execution(state, progress=0.9, current_node="persist_snapshot")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    context = state.get("context", {})

    graph_snapshot_id = f"gs_{uuid4().hex[:12]}"

    outputs = state.get("outputs", {})
    outputs["graph_snapshot_id"] = graph_snapshot_id
    outputs["nodes"] = intermediate.get("raw_nodes", [])
    outputs["edges"] = intermediate.get("raw_edges", [])
    state["outputs"] = outputs

    return state


async def finalize(state: GraphState) -> GraphState:
    """Finalize workflow."""
    state = update_execution(state, progress=1.0, current_node="finalize")

    if state["execution"]["status"] != "failed":
        state["execution"]["status"] = "completed"

    return state


def should_continue(state: GraphState) -> Literal["continue", "end"]:
    """Check if workflow should continue."""
    if state.get("execution", {}).get("status") == "failed":
        return "end"
    return "continue"


def create_graph_assembler_graph() -> StateGraph:
    """Create the Graph Assembler LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("fetch_case_findings", fetch_case_findings)
    workflow.add_node("query_subgraph", query_subgraph)
    workflow.add_node("fuse_annotate_provenance", fuse_annotate_provenance)
    workflow.add_node("build_layout", build_layout)
    workflow.add_node("persist_snapshot", persist_snapshot)
    workflow.add_node("finalize", finalize)

    # Set entry point
    workflow.set_entry_point("fetch_case_findings")

    # Add edges
    workflow.add_conditional_edges(
        "fetch_case_findings",
        should_continue,
        {"continue": "query_subgraph", "end": "finalize"},
    )
    workflow.add_edge("query_subgraph", "fuse_annotate_provenance")
    workflow.add_edge("fuse_annotate_provenance", "build_layout")
    workflow.add_edge("build_layout", "persist_snapshot")
    workflow.add_edge("persist_snapshot", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()
