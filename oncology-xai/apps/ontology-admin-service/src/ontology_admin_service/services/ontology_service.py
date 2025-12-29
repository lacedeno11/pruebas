"""Ontology service with business logic."""

import hashlib
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ontology_admin_service.models import (
    OntologyVersion,
    OntologyUpdateProposal,
    ProposalStatus,
)
from ontology_admin_service.config import settings
from langgraph_workflows.tools.reasoner import get_reasoner_client

logger = logging.getLogger(__name__)


class OntologyService:
    """Service for managing ontologies and proposals."""

    def __init__(self, db: AsyncSession):
        """Initialize service."""
        self.db = db
        self.reasoner = get_reasoner_client(settings.reasoner_backend)

    async def list_active_ontologies(self) -> list[OntologyVersion]:
        """List all active ontology versions."""
        result = await self.db.execute(
            select(OntologyVersion).where(OntologyVersion.is_active == True)
        )
        return list(result.scalars().all())

    async def get_ontology_version(self, version_id: UUID) -> OntologyVersion | None:
        """Get specific ontology version."""
        result = await self.db.execute(
            select(OntologyVersion).where(OntologyVersion.version_id == version_id)
        )
        return result.scalar_one_or_none()

    async def create_update_proposal(
        self,
        ontology_sources: list[str],
        mode: str,
        created_by: str | None = None,
        uploaded_files: dict | None = None,
    ) -> OntologyUpdateProposal:
        """Create a new ontology update proposal."""
        # Validate sources
        invalid_sources = set(ontology_sources) - set(settings.allowed_ontology_sources)
        if invalid_sources:
            raise ValueError(
                f"Invalid ontology sources: {invalid_sources}. "
                f"Allowed sources: {settings.allowed_ontology_sources}"
            )

        # Validate mode
        if mode not in ["online", "offline"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'online' or 'offline'")

        # For offline mode, require uploaded files
        if mode == "offline" and not uploaded_files:
            raise ValueError("Offline mode requires uploaded files")

        proposal = OntologyUpdateProposal(
            proposal_id=uuid4(),
            ontology_sources=ontology_sources,
            mode=mode,
            status=ProposalStatus.DRAFT,
            created_by=created_by,
            uploaded_files=uploaded_files or {},
        )

        self.db.add(proposal)
        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(
            f"Created update proposal {proposal.proposal_id} for sources {ontology_sources}"
        )

        return proposal

    async def get_proposal(self, proposal_id: UUID) -> OntologyUpdateProposal | None:
        """Get proposal by ID."""
        result = await self.db.execute(
            select(OntologyUpdateProposal).where(
                OntologyUpdateProposal.proposal_id == proposal_id
            )
        )
        return result.scalar_one_or_none()

    async def update_proposal_status(
        self,
        proposal_id: UUID,
        status: ProposalStatus,
        **kwargs,
    ) -> OntologyUpdateProposal:
        """Update proposal status."""
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        proposal.status = status

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(proposal, key):
                setattr(proposal, key, value)

        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(f"Updated proposal {proposal_id} status to {status}")

        return proposal

    async def run_validation(self, proposal_id: UUID) -> dict[str, Any]:
        """Run reasoner validation on proposal."""
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        # Update status to VALIDATING
        proposal.status = ProposalStatus.VALIDATING
        await self.db.flush()

        validation_results = {}
        errors = []

        # Get ontology data from uploaded files or workflow results
        ontology_data_map = proposal.uploaded_files.get("ontology_data", {})

        for source in proposal.ontology_sources:
            ontology_data = ontology_data_map.get(source)
            if not ontology_data:
                errors.append({
                    "source": source,
                    "error": "No ontology data available for validation",
                })
                continue

            try:
                # Run consistency check
                result = await self.reasoner.check_consistency(ontology_data)
                validation_results[source] = result

                if not result.get("consistent", True):
                    errors.append({
                        "source": source,
                        "error": "Ontology is inconsistent",
                        "details": result.get("errors", []),
                    })
            except Exception as e:
                logger.error(f"Validation error for {source}: {e}")
                errors.append({
                    "source": source,
                    "error": str(e),
                })

        # Update proposal with results
        proposal.reasoner_results = validation_results
        proposal.validation_errors = errors

        if errors:
            proposal.status = ProposalStatus.REQUIRES_FIX
        else:
            proposal.status = ProposalStatus.VALIDATED

        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(
            f"Validation completed for proposal {proposal_id}. "
            f"Errors: {len(errors)}, Status: {proposal.status}"
        )

        return {
            "proposal_id": str(proposal_id),
            "status": proposal.status.value,
            "validation_results": validation_results,
            "errors": errors,
        }

    async def approve_and_publish(
        self,
        proposal_id: UUID,
        approved_by: str,
        approval_notes: str | None = None,
    ) -> dict[str, Any]:
        """Approve and publish proposal."""
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        # Check if proposal is validated
        if proposal.status not in [ProposalStatus.VALIDATED, ProposalStatus.PENDING_APPROVAL]:
            raise ValueError(
                f"Cannot approve proposal in status {proposal.status}. "
                "Must be VALIDATED or PENDING_APPROVAL"
            )

        # Update proposal status
        proposal.status = ProposalStatus.APPROVED
        proposal.approved_by = approved_by
        proposal.approved_at = datetime.utcnow()
        proposal.approval_notes = approval_notes

        await self.db.flush()

        # Create ontology versions
        created_versions = []
        ontology_data_map = proposal.uploaded_files.get("ontology_data", {})

        for source in proposal.ontology_sources:
            ontology_data = ontology_data_map.get(source)
            if not ontology_data:
                logger.warning(f"No data for source {source}, skipping")
                continue

            # Compute hash
            content_hash = hashlib.sha256(
                ontology_data.encode() if isinstance(ontology_data, str) else ontology_data
            ).hexdigest()

            # Deactivate previous versions
            await self.db.execute(
                select(OntologyVersion)
                .where(
                    and_(
                        OntologyVersion.ontology_source == source,
                        OntologyVersion.is_active == True,
                    )
                )
            )
            previous_versions = (await self.db.execute(
                select(OntologyVersion).where(
                    and_(
                        OntologyVersion.ontology_source == source,
                        OntologyVersion.is_active == True,
                    )
                )
            )).scalars().all()

            new_version_id = uuid4()
            version_tag = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            # Create new version
            version = OntologyVersion(
                version_id=new_version_id,
                ontology_source=source,
                version_tag=version_tag,
                content_hash=content_hash,
                ontology_data=ontology_data,
                statistics=proposal.reasoner_results.get(source, {}).get("statistics", {}),
                is_active=True,
                published_by=approved_by,
                metadata_={
                    "proposal_id": str(proposal_id),
                    "diff_summary": proposal.diff_summary.get(source, {}),
                    "impact": proposal.impact_analysis.get(source, {}),
                },
            )

            self.db.add(version)
            created_versions.append(version)

            # Mark previous versions as replaced
            for prev_version in previous_versions:
                prev_version.is_active = False
                prev_version.replaced_by = new_version_id

        await self.db.flush()

        # Update proposal
        if created_versions:
            proposal.created_version_id = created_versions[0].version_id

        proposal.status = ProposalStatus.PUBLISHED

        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(
            f"Published proposal {proposal_id}. Created {len(created_versions)} versions"
        )

        return {
            "proposal_id": str(proposal_id),
            "status": proposal.status.value,
            "created_versions": [
                {
                    "version_id": str(v.version_id),
                    "source": v.ontology_source,
                    "version_tag": v.version_tag,
                }
                for v in created_versions
            ],
        }

    async def rollback_version(
        self,
        from_version_id: UUID,
        to_version_id: UUID | None,
        created_by: str,
    ) -> dict[str, Any]:
        """Rollback ontology version."""
        # Get the version to rollback from
        from_version = await self.get_ontology_version(from_version_id)
        if not from_version:
            raise ValueError(f"Version {from_version_id} not found")

        # If to_version_id is None, find the previous version
        if to_version_id is None:
            result = await self.db.execute(
                select(OntologyVersion)
                .where(
                    and_(
                        OntologyVersion.ontology_source == from_version.ontology_source,
                        OntologyVersion.version_id != from_version_id,
                        OntologyVersion.published_at < from_version.published_at,
                    )
                )
                .order_by(OntologyVersion.published_at.desc())
                .limit(1)
            )
            to_version = result.scalar_one_or_none()
            if not to_version:
                raise ValueError(
                    f"No previous version found for {from_version.ontology_source}"
                )
        else:
            to_version = await self.get_ontology_version(to_version_id)
            if not to_version:
                raise ValueError(f"Target version {to_version_id} not found")

        # Create rollback proposal
        proposal = OntologyUpdateProposal(
            proposal_id=uuid4(),
            ontology_sources=[from_version.ontology_source],
            mode="rollback",
            status=ProposalStatus.ROLLBACK_REQUESTED,
            rollback_from_version_id=from_version_id,
            rollback_to_version_id=to_version.version_id,
            created_by=created_by,
        )

        self.db.add(proposal)
        await self.db.flush()

        # Deactivate current version
        from_version.is_active = False

        # Reactivate target version
        to_version.is_active = True
        to_version.replaced_by = None

        # Update proposal
        proposal.status = ProposalStatus.ROLLED_BACK
        proposal.approved_by = created_by
        proposal.approved_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(
            f"Rolled back {from_version.ontology_source} from "
            f"{from_version.version_tag} to {to_version.version_tag}"
        )

        return {
            "proposal_id": str(proposal.proposal_id),
            "status": proposal.status.value,
            "rollback_from": {
                "version_id": str(from_version.version_id),
                "version_tag": from_version.version_tag,
            },
            "rollback_to": {
                "version_id": str(to_version.version_id),
                "version_tag": to_version.version_tag,
            },
        }

    async def compute_diff(
        self,
        source: str,
        new_data: str,
    ) -> dict[str, Any]:
        """Compute diff between current version and new data."""
        # Get current active version
        result = await self.db.execute(
            select(OntologyVersion).where(
                and_(
                    OntologyVersion.ontology_source == source,
                    OntologyVersion.is_active == True,
                )
            )
        )
        current_version = result.scalar_one_or_none()

        if not current_version:
            return {
                "source": source,
                "status": "new",
                "message": "No existing version found",
            }

        try:
            # Use reasoner to validate changes
            validation_result = await self.reasoner.validate_changes(
                current_version.ontology_data,
                new_data,
            )

            return {
                "source": source,
                "status": "diff_computed",
                "breaking_changes": validation_result.get("breaking_changes", []),
                "new_concepts": validation_result.get("new_concepts", []),
                "removed_concepts": validation_result.get("removed_concepts", []),
                "deprecations": validation_result.get("deprecations", []),
            }
        except Exception as e:
            logger.error(f"Error computing diff for {source}: {e}")
            return {
                "source": source,
                "status": "error",
                "error": str(e),
            }
