"""Database models for Ontology Admin Service."""

from ontology_admin_service.models.ontology_version import OntologyVersion
from ontology_admin_service.models.ontology_update_proposal import (
    OntologyUpdateProposal,
    ProposalStatus,
)

__all__ = [
    "OntologyVersion",
    "OntologyUpdateProposal",
    "ProposalStatus",
]
