"""SPARQL client for triple store operations."""

from typing import Any

import httpx


class SPARQLClient:
    """Client for Apache Jena Fuseki SPARQL endpoint."""

    def __init__(self, fuseki_url: str, dataset: str):
        self.fuseki_url = fuseki_url.rstrip("/")
        self.dataset = dataset
        self.query_endpoint = f"{self.fuseki_url}/{dataset}/query"
        self.update_endpoint = f"{self.fuseki_url}/{dataset}/update"
        self.data_endpoint = f"{self.fuseki_url}/{dataset}/data"

    async def query(
        self,
        sparql: str,
        accept: str = "application/sparql-results+json",
    ) -> dict[str, Any]:
        """Execute a SPARQL SELECT/ASK query."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.query_endpoint,
                data={"query": sparql},
                headers={"Accept": accept},
            )
            response.raise_for_status()
            return response.json()

    async def update(self, sparql: str) -> bool:
        """Execute a SPARQL UPDATE query."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.update_endpoint,
                data={"update": sparql},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return True

    async def upload_rdf(
        self,
        data: str | bytes,
        graph_uri: str | None = None,
        content_type: str = "text/turtle",
    ) -> bool:
        """Upload RDF data to a named graph."""
        url = self.data_endpoint
        if graph_uri:
            url = f"{url}?graph={graph_uri}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                content=data if isinstance(data, bytes) else data.encode(),
                headers={"Content-Type": content_type},
            )
            response.raise_for_status()
            return True

    async def get_graph(
        self,
        graph_uri: str,
        accept: str = "text/turtle",
    ) -> str:
        """Get RDF data from a named graph."""
        url = f"{self.data_endpoint}?graph={graph_uri}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Accept": accept})
            response.raise_for_status()
            return response.text

    async def delete_graph(self, graph_uri: str) -> bool:
        """Delete a named graph."""
        sparql = f"DROP GRAPH <{graph_uri}>"
        return await self.update(sparql)

    async def graph_exists(self, graph_uri: str) -> bool:
        """Check if a named graph exists."""
        sparql = f"""
        ASK WHERE {{
            GRAPH <{graph_uri}> {{ ?s ?p ?o }}
        }}
        """
        result = await self.query(sparql)
        return result.get("boolean", False)

    def query_sync(self, sparql: str) -> dict[str, Any]:
        """Synchronous query execution."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.query(sparql))
