"""SPARQL tool wrapper for LangGraph."""

import os

from oncology_common.clients.sparql import SPARQLClient


def get_sparql_tool(
    fuseki_url: str | None = None,
    dataset: str | None = None,
) -> SPARQLClient:
    """Get configured SPARQL client."""
    return SPARQLClient(
        fuseki_url=fuseki_url or os.getenv("FUSEKI_URL", "http://localhost:3030"),
        dataset=dataset or os.getenv("FUSEKI_DATASET", "oncology"),
    )
