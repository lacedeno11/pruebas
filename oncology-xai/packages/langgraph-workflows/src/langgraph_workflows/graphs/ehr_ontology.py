"""EHR to Ontology LangGraph workflow.

Nodes: NormalizeEHR → ExtractEntities → LookupCandidates →
       Disambiguate → BuildEvidencePack → PersistEntitiesMappings → Finalize
"""

from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph, END

from langgraph_workflows.state import GraphState, update_execution
from langgraph_workflows.tools.llm import get_llm_client
from langgraph_workflows.tools.sparql import get_sparql_tool


async def normalize_ehr(state: GraphState) -> GraphState:
    """Normalize EHR text."""
    state = update_execution(state, status="running", progress=0.0, current_node="normalize_ehr")

    inputs = state.get("inputs", {})
    ehr_text = inputs.get("ehr_text", "")

    if not ehr_text:
        state = update_execution(
            state,
            error={"code": "VALIDATION_ERROR", "message": "ehr_text required"},
        )
        state["execution"]["status"] = "failed"
        return state

    # Simple normalization: lowercase sections, remove extra whitespace
    normalized = " ".join(ehr_text.split())
    state["_current_ehr_text"] = normalized

    return state


async def extract_entities(state: GraphState) -> GraphState:
    """Extract clinical entities from EHR text."""
    state = update_execution(state, progress=0.2, current_node="extract_entities")

    if state["execution"]["status"] == "failed":
        return state

    ehr_text = state.get("_current_ehr_text", "")

    try:
        llm_client = get_llm_client()
        entity_types = ["DIAGNOSIS", "MUTATION", "PATTERN", "STAGE"]

        entities = await llm_client.extract_entities(ehr_text, entity_types)

        # Add entity IDs
        for i, entity in enumerate(entities):
            entity["entity_id"] = f"ent_{uuid4().hex[:12]}"

        outputs = state.get("outputs", {})
        outputs["ehr_entities"] = entities
        state["outputs"] = outputs

    except Exception as e:
        state = update_execution(
            state,
            error={"code": "EXTRACTION_ERROR", "message": str(e)},
        )
        state["execution"]["status"] = "failed"

    return state


async def lookup_candidates(state: GraphState) -> GraphState:
    """Look up ontology candidates for each entity."""
    state = update_execution(state, progress=0.4, current_node="lookup_candidates")

    if state["execution"]["status"] == "failed":
        return state

    outputs = state.get("outputs", {})
    entities = outputs.get("ehr_entities", [])

    # Mock ontology mappings
    ontology_mappings = {
        "adenocarcinoma": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C3512", "label": "Lung Adenocarcinoma"},
            {"ontology": "MONDO", "iri": "http://purl.obolibrary.org/obo/MONDO_0005061", "label": "lung adenocarcinoma"},
        ],
        "egfr": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C51744", "label": "EGFR Gene"},
            {"ontology": "SO", "iri": "http://purl.obolibrary.org/obo/SO_0000704", "label": "gene"},
        ],
        "kras": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C52541", "label": "KRAS Gene"},
        ],
        "tp53": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C17359", "label": "TP53 Gene"},
        ],
        "lepidic": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C136486", "label": "Lepidic Pattern"},
        ],
        "acinar": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C136487", "label": "Acinar Pattern"},
        ],
        "papillary": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C136488", "label": "Papillary Pattern"},
        ],
        "micropapillary": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C136489", "label": "Micropapillary Pattern"},
        ],
        "solid": [
            {"ontology": "NCIt", "iri": "http://purl.obolibrary.org/obo/NCIT_C136490", "label": "Solid Pattern"},
        ],
    }

    intermediate = state.get("_intermediate_results", {})
    candidates = []

    for entity in entities:
        text_lower = entity.get("text", "").lower()
        entity_candidates = ontology_mappings.get(text_lower, [])

        candidates.append({
            "entity_id": entity["entity_id"],
            "entity_text": entity["text"],
            "candidates": entity_candidates,
        })

    intermediate["candidates"] = candidates
    state["_intermediate_results"] = intermediate

    return state


async def disambiguate(state: GraphState) -> GraphState:
    """Disambiguate between candidate mappings."""
    state = update_execution(state, progress=0.6, current_node="disambiguate")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    candidates = intermediate.get("candidates", [])

    mappings = []
    for candidate_set in candidates:
        entity_id = candidate_set["entity_id"]

        for candidate in candidate_set.get("candidates", []):
            mapping_id = f"map_{uuid4().hex[:12]}"
            mappings.append({
                "mapping_id": mapping_id,
                "entity_id": entity_id,
                "ontology": candidate["ontology"],
                "iri": candidate["iri"],
                "label": candidate["label"],
                "confidence": 0.85,  # Mock confidence
                "mapping_method": "lexical_match",
            })

    outputs = state.get("outputs", {})
    outputs["ehr_mappings"] = mappings
    state["outputs"] = outputs

    return state


async def build_evidence_pack(state: GraphState) -> GraphState:
    """Build evidence pack for mappings."""
    state = update_execution(state, progress=0.75, current_node="build_evidence_pack")

    if state["execution"]["status"] == "failed":
        return state

    outputs = state.get("outputs", {})
    entities = outputs.get("ehr_entities", [])
    mappings = outputs.get("ehr_mappings", [])

    # Add evidence to mappings
    for mapping in mappings:
        entity = next(
            (e for e in entities if e["entity_id"] == mapping["entity_id"]),
            None
        )
        if entity:
            mapping["evidence"] = {
                "text_span": entity.get("text"),
                "start": entity.get("start"),
                "end": entity.get("end"),
                "section": entity.get("section"),
            }

    state["outputs"] = outputs

    return state


async def persist_entities_mappings(state: GraphState) -> GraphState:
    """Persist entities and mappings."""
    state = update_execution(state, progress=0.9, current_node="persist_entities_mappings")

    if state["execution"]["status"] == "failed":
        return state

    # In real implementation, would persist to database
    return state


async def finalize(state: GraphState) -> GraphState:
    """Finalize workflow."""
    state = update_execution(state, progress=1.0, current_node="finalize")

    if state["execution"]["status"] != "failed":
        state["execution"]["status"] = "completed"

    # Clean up transient data
    state.pop("_current_ehr_text", None)

    return state


def should_continue(state: GraphState) -> Literal["continue", "end"]:
    """Check if workflow should continue."""
    if state.get("execution", {}).get("status") == "failed":
        return "end"
    return "continue"


def create_ehr_ontology_graph() -> StateGraph:
    """Create the EHR to Ontology LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("normalize_ehr", normalize_ehr)
    workflow.add_node("extract_entities", extract_entities)
    workflow.add_node("lookup_candidates", lookup_candidates)
    workflow.add_node("disambiguate", disambiguate)
    workflow.add_node("build_evidence_pack", build_evidence_pack)
    workflow.add_node("persist_entities_mappings", persist_entities_mappings)
    workflow.add_node("finalize", finalize)

    # Set entry point
    workflow.set_entry_point("normalize_ehr")

    # Add edges
    workflow.add_conditional_edges(
        "normalize_ehr",
        should_continue,
        {"continue": "extract_entities", "end": "finalize"},
    )
    workflow.add_conditional_edges(
        "extract_entities",
        should_continue,
        {"continue": "lookup_candidates", "end": "finalize"},
    )
    workflow.add_edge("lookup_candidates", "disambiguate")
    workflow.add_edge("disambiguate", "build_evidence_pack")
    workflow.add_edge("build_evidence_pack", "persist_entities_mappings")
    workflow.add_edge("persist_entities_mappings", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()
