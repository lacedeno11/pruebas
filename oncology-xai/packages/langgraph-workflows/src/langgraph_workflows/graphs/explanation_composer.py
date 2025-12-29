"""Explanation Composer LangGraph workflow.

Nodes: GatherEvidence → DetectConflicts → DraftExplanation →
       ValidateClaimsGuardrails → PublishReport → Finalize
"""

import re
from typing import Any, Literal
from uuid import uuid4

from langgraph.graph import StateGraph, END

from langgraph_workflows.state import GraphState, update_execution
from langgraph_workflows.tools.llm import get_llm_client


# Clinical guardrails - prohibited phrases
PROHIBITED_PHRASES = [
    r"\bis\s+definitely\b",
    r"\bconfirmed\s+diagnosis\b",
    r"\bdefinitive\s+diagnosis\b",
    r"\bpatient\s+has\b",
    r"\bdiagnosed\s+with\b",
    r"\bwe\s+can\s+confirm\b",
    r"\bthis\s+is\s+cancer\b",
    r"\bmalignant\s+confirmed\b",
]


async def gather_evidence(state: GraphState) -> GraphState:
    """Gather evidence from all sources."""
    state = update_execution(state, status="running", progress=0.0, current_node="gather_evidence")

    outputs = state.get("outputs", {})
    context = state.get("context", {})

    # Collect evidence from state
    evidence = {
        "case_id": context.get("case_id"),
        "pattern_results": outputs.get("pattern_outputs", []),
        "mutation_results": outputs.get("genetic_outputs", []),
        "ehr_entities": outputs.get("ehr_entities", []),
        "ehr_mappings": outputs.get("ehr_mappings", []),
        "graph_nodes": outputs.get("nodes", []),
        "graph_edges": outputs.get("edges", []),
    }

    intermediate = state.get("_intermediate_results", {})
    intermediate["evidence"] = evidence
    state["_intermediate_results"] = intermediate

    return state


async def detect_conflicts(state: GraphState) -> GraphState:
    """Detect conflicts between sources."""
    state = update_execution(state, progress=0.2, current_node="detect_conflicts")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    evidence = intermediate.get("evidence", {})

    conflicts = []

    # Check for EHR vs image conflicts
    ehr_entities = evidence.get("ehr_entities", [])
    mutation_results = evidence.get("mutation_results", [])

    # Look for mutation mentions in EHR
    ehr_mutations = [e for e in ehr_entities if e.get("type") == "MUTATION"]

    for ehr_mut in ehr_mutations:
        ehr_text = ehr_mut.get("text", "").upper()

        for img_mut in mutation_results:
            if img_mut.get("mutation", "").upper() in ehr_text:
                # Check for conflict
                if "positive" in ehr_text.lower() and img_mut.get("status") == "NEG":
                    conflicts.append({
                        "type": "mutation_discrepancy",
                        "mutation": img_mut["mutation"],
                        "ehr_claim": "positive",
                        "image_result": "negative",
                        "severity": "high",
                    })
                elif "negative" in ehr_text.lower() and img_mut.get("status") == "POS":
                    conflicts.append({
                        "type": "mutation_discrepancy",
                        "mutation": img_mut["mutation"],
                        "ehr_claim": "negative",
                        "image_result": "positive",
                        "severity": "high",
                    })

    outputs = state.get("outputs", {})
    outputs["conflicts"] = conflicts
    state["outputs"] = outputs

    intermediate["has_conflicts"] = len(conflicts) > 0
    state["_intermediate_results"] = intermediate

    return state


async def draft_explanation(state: GraphState) -> GraphState:
    """Draft explanation using LLM or template."""
    state = update_execution(state, progress=0.5, current_node="draft_explanation")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    evidence = intermediate.get("evidence", {})
    outputs = state.get("outputs", {})
    policies = state.get("policies", {})

    findings = {
        "patterns": evidence.get("pattern_results", []),
        "mutations": evidence.get("mutation_results", []),
        "conflicts": outputs.get("conflicts", []),
    }

    try:
        llm_client = get_llm_client()
        explanation = await llm_client.generate_explanation(findings, evidence)

        intermediate["draft_explanation"] = explanation
        state["_intermediate_results"] = intermediate

    except Exception as e:
        state = update_execution(
            state,
            error={"code": "EXPLANATION_ERROR", "message": str(e)},
        )
        # Use fallback template
        intermediate["draft_explanation"] = _generate_template_explanation(findings, evidence)
        state["_intermediate_results"] = intermediate

    return state


def _generate_template_explanation(findings: dict, evidence: dict) -> str:
    """Generate explanation using template (fallback)."""
    patterns = findings.get("patterns", [])
    mutations = findings.get("mutations", [])
    conflicts = findings.get("conflicts", [])

    html = """<!DOCTYPE html>
<html>
<head>
    <title>Clinical Explanation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 1px solid #ccc; }
        .warning { background: #fff3cd; padding: 10px; border-radius: 5px; }
        .score { font-weight: bold; }
        .inconclusive { color: #dc3545; }
        .positive { color: #28a745; }
        .limitations { background: #f8f9fa; padding: 15px; border-left: 4px solid #6c757d; }
    </style>
</head>
<body>
    <h1>Clinical Findings Report</h1>
    <p class="warning"><strong>IMPORTANT:</strong> This is an AI-assisted analysis.
    All findings should be confirmed by a qualified pathologist before clinical use.</p>

    <h2>Histological Patterns</h2>
    <table border="1" cellpadding="10">
        <tr><th>Pattern</th><th>Score</th><th>Status</th></tr>
"""

    for p in patterns:
        status_class = "" if p.get("is_conclusive") else "inconclusive"
        status = "Detected" if p.get("is_conclusive") else "Inconclusive"
        html += f"""        <tr>
            <td>{p.get('pattern', 'Unknown')}</td>
            <td class="score">{p.get('score', 0):.2f}</td>
            <td class="{status_class}">{status}</td>
        </tr>
"""

    html += """    </table>

    <h2>Genetic Mutation Analysis</h2>
    <table border="1" cellpadding="10">
        <tr><th>Mutation</th><th>Score</th><th>Status</th></tr>
"""

    for m in mutations:
        status = m.get("status", "INCONCLUSIVE")
        status_class = "positive" if status == "POS" else ("inconclusive" if status == "INCONCLUSIVE" else "")
        html += f"""        <tr>
            <td>{m.get('mutation', 'Unknown')}</td>
            <td class="score">{m.get('score', 0):.2f}</td>
            <td class="{status_class}">{status}</td>
        </tr>
"""

    html += """    </table>
"""

    if conflicts:
        html += """
    <h2>Detected Conflicts</h2>
    <div class="warning">
        <p><strong>The following conflicts were detected between sources:</strong></p>
        <ul>
"""
        for c in conflicts:
            html += f"""            <li>{c.get('type')}: {c.get('mutation')} -
                EHR claims {c.get('ehr_claim')}, Image analysis shows {c.get('image_result')}</li>
"""
        html += """        </ul>
    </div>
"""

    html += """
    <h2>Limitations</h2>
    <div class="limitations">
        <ul>
            <li>This analysis is for research and educational purposes only.</li>
            <li>Results are based on AI-assisted pattern recognition and should not be used as definitive diagnosis.</li>
            <li>All findings must be confirmed by qualified medical professionals.</li>
            <li>Model performance may vary based on image quality and sample preparation.</li>
        </ul>
    </div>

    <h2>Technical Details</h2>
    <p><strong>Model Version:</strong> mock_v1.0</p>
    <p><strong>Ontology Versions:</strong> NCIt 23.10, MONDO 2023-10-01, SO 2.0</p>

    <hr>
    <p><em>Generated by DERCAS-ONCO-XAI</em></p>
</body>
</html>
"""
    return html


async def validate_claims_guardrails(state: GraphState) -> GraphState:
    """Validate explanation against clinical guardrails."""
    state = update_execution(state, progress=0.75, current_node="validate_claims_guardrails")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    explanation = intermediate.get("draft_explanation", "")

    violations = []

    # Check for prohibited phrases
    for pattern in PROHIBITED_PHRASES:
        if re.search(pattern, explanation, re.IGNORECASE):
            violations.append({
                "rule": "prohibited_phrase",
                "pattern": pattern,
                "severity": "error",
            })

    # Check for required sections
    required_sections = ["Limitations", "Model Version"]
    for section in required_sections:
        if section.lower() not in explanation.lower():
            violations.append({
                "rule": "missing_section",
                "section": section,
                "severity": "warning",
            })

    outputs = state.get("outputs", {})

    if any(v["severity"] == "error" for v in violations):
        # Guardrails failed - need to regenerate or fix
        state = update_execution(
            state,
            error={"code": "GUARDRAILS_VIOLATION", "message": f"{len(violations)} violations found"},
        )
        outputs["guardrails_passed"] = False
    else:
        outputs["guardrails_passed"] = True

    outputs["guardrails_violations"] = [v["rule"] for v in violations]
    state["outputs"] = outputs

    return state


async def publish_report(state: GraphState) -> GraphState:
    """Publish the explanation report."""
    state = update_execution(state, progress=0.9, current_node="publish_report")

    if state["execution"]["status"] == "failed":
        return state

    intermediate = state.get("_intermediate_results", {})
    context = state.get("context", {})
    outputs = state.get("outputs", {})

    report_id = f"rep_{uuid4().hex[:12]}"

    # In real implementation, would save to storage
    outputs["explanation_report_id"] = report_id
    outputs["report_uri"] = f"s3://oncology-xai/reports/{context.get('case_id')}/{report_id}.html"
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


def create_explanation_composer_graph() -> StateGraph:
    """Create the Explanation Composer LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("gather_evidence", gather_evidence)
    workflow.add_node("detect_conflicts", detect_conflicts)
    workflow.add_node("draft_explanation", draft_explanation)
    workflow.add_node("validate_claims_guardrails", validate_claims_guardrails)
    workflow.add_node("publish_report", publish_report)
    workflow.add_node("finalize", finalize)

    # Set entry point
    workflow.set_entry_point("gather_evidence")

    # Add edges
    workflow.add_edge("gather_evidence", "detect_conflicts")
    workflow.add_edge("detect_conflicts", "draft_explanation")
    workflow.add_edge("draft_explanation", "validate_claims_guardrails")
    workflow.add_conditional_edges(
        "validate_claims_guardrails",
        should_continue,
        {"continue": "publish_report", "end": "finalize"},
    )
    workflow.add_edge("publish_report", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()
