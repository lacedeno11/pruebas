"""Ontology Update LangGraph workflow.

Nodes: SourceDiscovery → FetchOntology → ValidateIntegrity → ParseRDF →
       ComputeDiff → LLMMappingSuggestions → ReasonerCheck → ImpactAnalysis →
       CreateProposal → HITLApproval → PublishOrRollback
"""

import hashlib
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph, END

from langgraph_workflows.state import GraphState, update_execution
from langgraph_workflows.tools.reasoner import get_reasoner_client


# Whitelisted ontology sources
WHITELISTED_SOURCES = {
    "NCIt": "https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/",
    "MONDO": "http://purl.obolibrary.org/obo/mondo.owl",
    "SO": "http://purl.obolibrary.org/obo/so.owl",
}


async def source_discovery(state: GraphState) -> GraphState:
    """Discover ontology sources."""
    state = update_execution(state, status="running", progress=0.0, current_node="source_discovery")

    inputs = state.get("inputs", {})
    targets = inputs.get("ontology_targets", ["NCIt"])
    mode = inputs.get("mode", "offline")

    intermediate = state.get("_intermediate_results", {})

    if mode == "online":
        # Validate against whitelist
        sources = {}
        for target in targets:
            if target in WHITELISTED_SOURCES:
                sources[target] = WHITELISTED_SOURCES[target]
            else:
                state = update_execution(
                    state,
                    error={"code": "SOURCE_NOT_ALLOWED", "message": f"Source {target} not in whitelist"},
                )
                state["execution"]["status"] = "failed"
                return state

        intermediate["sources"] = sources
    else:
        # Offline mode - expect file uploads
        intermediate["sources"] = {t: "local_upload" for t in targets}

    intermediate["mode"] = mode
    state["_intermediate_results"] = intermediate

    return state


async def fetch_ontology(state: GraphState) -> GraphState:
    """Fetch ontology from sources."""
    state = update_execution(state, progress=0.1, current_node="fetch_ontology")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    mode = intermediate.get("mode", "offline")

    # Mock ontology data
    mock_ontology = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ncit: <http://purl.obolibrary.org/obo/NCIT_> .

ncit:C3512 a owl:Class ;
    rdfs:label "Lung Adenocarcinoma" ;
    rdfs:subClassOf ncit:C4878 .

ncit:C136486 a owl:Class ;
    rdfs:label "Lepidic Pattern" .

ncit:C136487 a owl:Class ;
    rdfs:label "Acinar Pattern" .
"""

    intermediate["ontology_data"] = {
        "NCIt": mock_ontology,
    }
    state["_intermediate_results"] = intermediate

    return state


async def validate_integrity(state: GraphState) -> GraphState:
    """Validate ontology integrity (hash, signature)."""
    state = update_execution(state, progress=0.2, current_node="validate_integrity")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    ontology_data = intermediate.get("ontology_data", {})

    hashes = {}
    for name, data in ontology_data.items():
        content = data if isinstance(data, bytes) else data.encode()
        hashes[name] = hashlib.sha256(content).hexdigest()

    intermediate["hashes"] = hashes
    state["_intermediate_results"] = intermediate

    return state


async def parse_rdf(state: GraphState) -> GraphState:
    """Parse RDF ontology data."""
    state = update_execution(state, progress=0.3, current_node="parse_rdf")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    ontology_data = intermediate.get("ontology_data", {})

    # Mock parsing - count triples/classes
    stats = {}
    for name, data in ontology_data.items():
        stats[name] = {
            "classes": data.count("owl:Class"),
            "properties": data.count("owl:ObjectProperty") + data.count("owl:DatatypeProperty"),
            "triples_estimate": data.count(" ."),
        }

    intermediate["parse_stats"] = stats
    state["_intermediate_results"] = intermediate

    return state


async def compute_diff(state: GraphState) -> GraphState:
    """Compute diff with current ontology version."""
    state = update_execution(state, progress=0.4, current_node="compute_diff")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    stats = intermediate.get("parse_stats", {})

    # Mock diff
    diff = {}
    for name, stat in stats.items():
        diff[name] = {
            "added_classes": 2,
            "removed_classes": 0,
            "modified_labels": 1,
            "new_relationships": 3,
        }

    intermediate["diff"] = diff
    state["_intermediate_results"] = intermediate

    return state


async def llm_mapping_suggestions(state: GraphState) -> GraphState:
    """Generate LLM-based mapping suggestions."""
    state = update_execution(state, progress=0.5, current_node="llm_mapping_suggestions")

    if state["execution"]["status"] == "failed":
        return state

    # Mock suggestions
    intermediate = state.get("_intermediate_results", {})
    intermediate["mapping_suggestions"] = [
        {
            "source": "NCIt:C3512",
            "target": "MONDO:0005061",
            "type": "equivalentClass",
            "confidence": 0.95,
        },
    ]
    state["_intermediate_results"] = intermediate

    return state


async def reasoner_check(state: GraphState) -> GraphState:
    """Run reasoner consistency check."""
    state = update_execution(state, progress=0.6, current_node="reasoner_check")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    ontology_data = intermediate.get("ontology_data", {})

    reasoner = get_reasoner_client()

    results = {}
    for name, data in ontology_data.items():
        result = await reasoner.check_consistency(data)
        results[name] = result

        if not result.get("consistent", True):
            state = update_execution(
                state,
                error={"code": "REASONER_FAILED", "message": f"Ontology {name} is inconsistent"},
            )
            state["execution"]["status"] = "failed"
            return state

    intermediate["reasoner_results"] = results
    state["_intermediate_results"] = intermediate

    return state


async def impact_analysis(state: GraphState) -> GraphState:
    """Analyze impact of changes."""
    state = update_execution(state, progress=0.7, current_node="impact_analysis")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    diff = intermediate.get("diff", {})

    # Calculate impact score
    impact = {}
    for name, changes in diff.items():
        total_changes = sum(changes.values())
        impact[name] = {
            "score": "low" if total_changes < 10 else ("medium" if total_changes < 50 else "high"),
            "breaking_changes": changes.get("removed_classes", 0),
            "affected_mappings": total_changes * 2,  # Estimate
        }

    intermediate["impact"] = impact
    state["_intermediate_results"] = intermediate

    return state


async def create_proposal(state: GraphState) -> GraphState:
    """Create update proposal."""
    state = update_execution(state, progress=0.8, current_node="create_proposal")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    identity = state.get("identity", {})

    proposal_id = f"prop_{uuid4().hex[:12]}"

    proposal = {
        "proposal_id": proposal_id,
        "targets": list(intermediate.get("sources", {}).keys()),
        "mode": intermediate.get("mode"),
        "status": "PENDING_APPROVAL",
        "diff_summary": intermediate.get("diff"),
        "impact": intermediate.get("impact"),
        "reasoner_results": intermediate.get("reasoner_results"),
        "hashes": intermediate.get("hashes"),
        "created_by": identity.get("user_id"),
    }

    intermediate["proposal"] = proposal
    state["_intermediate_results"] = intermediate

    outputs = state.get("outputs", {})
    outputs["proposal_id"] = proposal_id
    state["outputs"] = outputs

    return state


async def hitl_approval(state: GraphState) -> GraphState:
    """Human-in-the-loop approval checkpoint."""
    state = update_execution(state, progress=0.85, current_node="hitl_approval")

    if state["execution"]["status"] == "failed":
        return state

    # In real implementation, this would wait for admin approval
    # For now, auto-approve if impact is low
    intermediate = state.get("_intermediate_results", {})
    impact = intermediate.get("impact", {})

    all_low = all(i.get("score") == "low" for i in impact.values())

    intermediate["approved"] = all_low
    intermediate["approval_status"] = "auto_approved" if all_low else "pending_manual_review"
    state["_intermediate_results"] = intermediate

    return state


async def publish_or_rollback(state: GraphState) -> GraphState:
    """Publish or rollback based on approval."""
    state = update_execution(state, progress=0.95, current_node="publish_or_rollback")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    approved = intermediate.get("approved", False)

    outputs = state.get("outputs", {})

    if approved:
        # Mock publish
        outputs["published"] = True
        outputs["version_tag"] = f"v{uuid4().hex[:8]}"
        intermediate["proposal"]["status"] = "PUBLISHED"
    else:
        outputs["published"] = False
        intermediate["proposal"]["status"] = "PENDING_APPROVAL"

    state["outputs"] = outputs
    state["_intermediate_results"] = intermediate

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


def create_ontology_update_graph() -> StateGraph:
    """Create the Ontology Update LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("source_discovery", source_discovery)
    workflow.add_node("fetch_ontology", fetch_ontology)
    workflow.add_node("validate_integrity", validate_integrity)
    workflow.add_node("parse_rdf", parse_rdf)
    workflow.add_node("compute_diff", compute_diff)
    workflow.add_node("llm_mapping_suggestions", llm_mapping_suggestions)
    workflow.add_node("reasoner_check", reasoner_check)
    workflow.add_node("impact_analysis", impact_analysis)
    workflow.add_node("create_proposal", create_proposal)
    workflow.add_node("hitl_approval", hitl_approval)
    workflow.add_node("publish_or_rollback", publish_or_rollback)
    workflow.add_node("finalize", finalize)

    # Set entry point
    workflow.set_entry_point("source_discovery")

    # Add edges
    workflow.add_conditional_edges(
        "source_discovery",
        should_continue,
        {"continue": "fetch_ontology", "end": "finalize"},
    )
    workflow.add_edge("fetch_ontology", "validate_integrity")
    workflow.add_edge("validate_integrity", "parse_rdf")
    workflow.add_edge("parse_rdf", "compute_diff")
    workflow.add_edge("compute_diff", "llm_mapping_suggestions")
    workflow.add_edge("llm_mapping_suggestions", "reasoner_check")
    workflow.add_conditional_edges(
        "reasoner_check",
        should_continue,
        {"continue": "impact_analysis", "end": "finalize"},
    )
    workflow.add_edge("impact_analysis", "create_proposal")
    workflow.add_edge("create_proposal", "hitl_approval")
    workflow.add_edge("hitl_approval", "publish_or_rollback")
    workflow.add_edge("publish_or_rollback", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()
