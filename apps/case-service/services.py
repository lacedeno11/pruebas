"""
DERCAS-ONCO-XAI V1 - Case Service Business Logic

Business logic services for patient and case management.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Import shared packages
import sys
sys.path.append('/tmp/workspace/pruebas')

from packages.common.models import CaseStatus
from packages.common.errors import (
    ErrorCode,
    ResourceNotFoundError,
    ResourceConflictError,
    BusinessLogicError,
    ValidationError
)

from .models import Patient, Case
from .schemas import (
    PatientCreate,
    PatientUpdate,
    CaseCreate,
    CaseUpdate,
    CaseSearchFilters,
    PatientSearchFilters
)

logger = logging.getLogger(__name__)


class PatientService:
    """Service for patient management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_patient(self, patient_data: PatientCreate) -> Patient:
        """
        Create a new patient.
        
        Args:
            patient_data: Patient creation data
            
        Returns:
            Patient: Created patient
            
        Raises:
            ResourceConflictError: If patient ID already exists
        """
        # Check if patient ID already exists
        existing_patient = await self.get_patient_by_external_id(patient_data.patient_id)
        if existing_patient:
            raise ResourceConflictError(
                message=f"Patient with ID '{patient_data.patient_id}' already exists"
            )
        
        # Create new patient
        patient = Patient(
            patient_id=patient_data.patient_id,
            age=patient_data.age,
            gender=patient_data.gender,
            medical_record_number=patient_data.medical_record_number,
            diagnosis_date=patient_data.diagnosis_date,
            primary_site=patient_data.primary_site,
            histology=patient_data.histology,
            stage=patient_data.stage
        )
        
        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)
        
        logger.info(f"Created patient: {patient.id} ({patient.patient_id})")
        return patient
    
    async def get_patient_by_id(self, patient_id: UUID) -> Optional[Patient]:
        """
        Get patient by internal ID.
        
        Args:
            patient_id: Internal patient ID
            
        Returns:
            Patient: Patient or None if not found
        """
        stmt = select(Patient).where(Patient.id == patient_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_patient_by_external_id(self, patient_id: str) -> Optional[Patient]:
        """
        Get patient by external patient ID.
        
        Args:
            patient_id: External patient ID
            
        Returns:
            Patient: Patient or None if not found
        """
        stmt = select(Patient).where(Patient.patient_id == patient_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_patient(self, patient_id: UUID, patient_update: PatientUpdate) -> Optional[Patient]:
        """
        Update a patient.
        
        Args:
            patient_id: Internal patient ID
            patient_update: Update data
            
        Returns:
            Patient: Updated patient or None if not found
        """
        patient = await self.get_patient_by_id(patient_id)
        if not patient:
            return None
        
        # Update fields
        update_data = patient_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(patient, field, value)
        
        patient.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(patient)
        
        logger.info(f"Updated patient: {patient.id} ({patient.patient_id})")
        return patient
    
    async def list_patients(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[PatientSearchFilters] = None
    ) -> Tuple[List[Patient], int]:
        """
        List patients with pagination and filtering.
        
        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            filters: Search filters
            
        Returns:
            Tuple[List[Patient], int]: List of patients and total count
        """
        # Build base query
        stmt = select(Patient)
        count_stmt = select(func.count(Patient.id))
        
        # Apply filters
        if filters:
            conditions = []
            
            if filters.age_min is not None:
                conditions.append(Patient.age >= filters.age_min)
            
            if filters.age_max is not None:
                conditions.append(Patient.age <= filters.age_max)
            
            if filters.gender:
                conditions.append(Patient.gender.ilike(f"%{filters.gender}%"))
            
            if filters.primary_site:
                conditions.append(Patient.primary_site.ilike(f"%{filters.primary_site}%"))
            
            if filters.histology:
                conditions.append(Patient.histology.ilike(f"%{filters.histology}%"))
            
            if filters.stage:
                conditions.append(Patient.stage.ilike(f"%{filters.stage}%"))
            
            if conditions:
                stmt = stmt.where(and_(*conditions))
                count_stmt = count_stmt.where(and_(*conditions))
        
        # Get total count
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()
        
        # Apply pagination and ordering
        stmt = stmt.order_by(Patient.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        patients = result.scalars().all()
        
        return list(patients), total
    
    async def delete_patient(self, patient_id: UUID) -> bool:
        """
        Delete a patient.
        
        Args:
            patient_id: Internal patient ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        patient = await self.get_patient_by_id(patient_id)
        if not patient:
            return False
        
        await self.db.delete(patient)
        await self.db.commit()
        
        logger.info(f"Deleted patient: {patient_id}")
        return True


class CaseService:
    """Service for case management operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_case(self, case_data: CaseCreate) -> Case:
        """
        Create a new case.
        
        Args:
            case_data: Case creation data
            
        Returns:
            Case: Created case
            
        Raises:
            ResourceConflictError: If case ID already exists
            ResourceNotFoundError: If patient not found
        """
        # Check if case ID already exists
        existing_case = await self.get_case_by_external_id(case_data.case_id)
        if existing_case:
            raise ResourceConflictError(
                message=f"Case with ID '{case_data.case_id}' already exists"
            )
        
        # Verify patient exists
        patient_service = PatientService(self.db)
        patient = await patient_service.get_patient_by_id(case_data.patient_id)
        if not patient:
            raise ResourceNotFoundError(
                resource_type="Patient",
                resource_id=str(case_data.patient_id)
            )
        
        # Create new case
        case = Case(
            case_id=case_data.case_id,
            patient_id=case_data.patient_id,
            title=case_data.title,
            description=case_data.description,
            priority=case_data.priority,
            clinical_context=case_data.clinical_context,
            assigned_to=case_data.assigned_to,
            status=CaseStatus.CREATED
        )
        
        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)
        
        logger.info(f"Created case: {case.id} ({case.case_id})")
        return case
    
    async def get_case_by_id(self, case_id: UUID) -> Optional[Case]:
        """
        Get case by internal ID.
        
        Args:
            case_id: Internal case ID
            
        Returns:
            Case: Case or None if not found
        """
        stmt = select(Case).options(selectinload(Case.patient)).where(Case.id == case_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_case_by_external_id(self, case_id: str) -> Optional[Case]:
        """
        Get case by external case ID.
        
        Args:
            case_id: External case ID
            
        Returns:
            Case: Case or None if not found
        """
        stmt = select(Case).options(selectinload(Case.patient)).where(Case.case_id == case_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_case(self, case_id: str, case_update: CaseUpdate) -> Optional[Case]:
        """
        Update a case.
        
        Args:
            case_id: External case ID
            case_update: Update data
            
        Returns:
            Case: Updated case or None if not found
            
        Raises:
            BusinessLogicError: If status transition is invalid
        """
        case = await self.get_case_by_external_id(case_id)
        if not case:
            return None
        
        # Validate status transition if status is being updated
        if case_update.status and case_update.status != case.status:
            if not case.can_transition_to(case_update.status):
                raise BusinessLogicError(
                    error_code=ErrorCode.INVALID_CASE_STATUS,
                    message=f"Cannot transition case from {case.status} to {case_update.status}"
                )
        
        # Update fields
        update_data = case_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(case, field, value)
        
        # Set processing timestamps based on status
        if case_update.status:
            if case_update.status == CaseStatus.PROCESSING and not case.processing_started_at:
                case.processing_started_at = datetime.utcnow()
            elif case_update.status == CaseStatus.CLOSED and not case.processing_completed_at:
                case.processing_completed_at = datetime.utcnow()
        
        case.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(case)
        
        logger.info(f"Updated case: {case.id} ({case.case_id})")
        return case
    
    async def list_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[CaseStatus] = None,
        patient_id: Optional[str] = None,
        filters: Optional[CaseSearchFilters] = None
    ) -> Tuple[List[Case], int]:
        """
        List cases with pagination and filtering.
        
        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            status: Filter by case status
            patient_id: Filter by patient ID
            filters: Additional search filters
            
        Returns:
            Tuple[List[Case], int]: List of cases and total count
        """
        # Build base query
        stmt = select(Case).options(selectinload(Case.patient))
        count_stmt = select(func.count(Case.id))
        
        # Apply basic filters
        conditions = []
        
        if status:
            conditions.append(Case.status == status)
        
        if patient_id:
            # Join with patient to filter by external patient ID
            stmt = stmt.join(Patient)
            count_stmt = count_stmt.join(Patient)
            conditions.append(Patient.patient_id == patient_id)
        
        # Apply advanced filters
        if filters:
            if filters.assigned_to:
                conditions.append(Case.assigned_to.ilike(f"%{filters.assigned_to}%"))
            
            if filters.priority_min is not None:
                conditions.append(Case.priority >= filters.priority_min)
            
            if filters.priority_max is not None:
                conditions.append(Case.priority <= filters.priority_max)
            
            if filters.created_after:
                conditions.append(Case.created_at >= filters.created_after)
            
            if filters.created_before:
                conditions.append(Case.created_at <= filters.created_before)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        
        # Get total count
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar()
        
        # Apply pagination and ordering
        stmt = stmt.order_by(Case.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        cases = result.scalars().all()
        
        return list(cases), total
    
    async def get_cases_by_status(self, status: CaseStatus) -> List[Case]:
        """
        Get all cases with a specific status.
        
        Args:
            status: Case status to filter by
            
        Returns:
            List[Case]: List of cases with the specified status
        """
        stmt = select(Case).options(selectinload(Case.patient)).where(Case.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_active_cases(self) -> List[Case]:
        """
        Get all active cases (CREATED, READY, PROCESSING).
        
        Returns:
            List[Case]: List of active cases
        """
        active_statuses = [CaseStatus.CREATED, CaseStatus.READY, CaseStatus.PROCESSING]
        stmt = select(Case).options(selectinload(Case.patient)).where(Case.status.in_(active_statuses))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_cases_requiring_review(self) -> List[Case]:
        """
        Get all cases requiring review.
        
        Returns:
            List[Case]: List of cases requiring review
        """
        return await self.get_cases_by_status(CaseStatus.REVIEW_REQUIRED)
    
    async def transition_case_status(
        self,
        case_id: str,
        new_status: CaseStatus,
        reason: Optional[str] = None
    ) -> Optional[Case]:
        """
        Transition a case to a new status.
        
        Args:
            case_id: External case ID
            new_status: New status
            reason: Reason for status change
            
        Returns:
            Case: Updated case or None if not found
            
        Raises:
            BusinessLogicError: If status transition is invalid
        """
        case = await self.get_case_by_external_id(case_id)
        if not case:
            return None
        
        if not case.can_transition_to(new_status):
            raise BusinessLogicError(
                error_code=ErrorCode.INVALID_CASE_STATUS,
                message=f"Cannot transition case from {case.status} to {new_status}"
            )
        
        # Update status and related fields
        case.status = new_status
        case.updated_at = datetime.utcnow()
        
        if new_status == CaseStatus.PROCESSING and not case.processing_started_at:
            case.processing_started_at = datetime.utcnow()
        elif new_status == CaseStatus.CLOSED and not case.processing_completed_at:
            case.processing_completed_at = datetime.utcnow()
        elif new_status == CaseStatus.REVIEW_REQUIRED and reason:
            case.review_required_reason = reason
        
        await self.db.commit()
        await self.db.refresh(case)
        
        logger.info(f"Transitioned case {case_id} from {case.status} to {new_status}")
        return case
    
    async def assign_case(self, case_id: str, assigned_to: str) -> Optional[Case]:
        """
        Assign a case to a clinician.
        
        Args:
            case_id: External case ID
            assigned_to: Clinician identifier
            
        Returns:
            Case: Updated case or None if not found
        """
        case = await self.get_case_by_external_id(case_id)
        if not case:
            return None
        
        case.assigned_to = assigned_to
        case.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(case)
        
        logger.info(f"Assigned case {case_id} to {assigned_to}")
        return case
    
    async def delete_case(self, case_id: str) -> bool:
        """
        Delete a case.
        
        Args:
            case_id: External case ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        case = await self.get_case_by_external_id(case_id)
        if not case:
            return False
        
        await self.db.delete(case)
        await self.db.commit()
        
        logger.info(f"Deleted case: {case_id}")
        return True
    
    async def get_case_statistics(self) -> dict:
        """
        Get case statistics.
        
        Returns:
            dict: Case statistics
        """
        # Total cases
        total_stmt = select(func.count(Case.id))
        total_result = await self.db.execute(total_stmt)
        total_cases = total_result.scalar()
        
        # Cases by status
        status_stmt = select(Case.status, func.count(Case.id)).group_by(Case.status)
        status_result = await self.db.execute(status_stmt)
        cases_by_status = {status.value: count for status, count in status_result.all()}
        
        # Cases by priority
        priority_stmt = select(Case.priority, func.count(Case.id)).group_by(Case.priority)
        priority_result = await self.db.execute(priority_stmt)
        cases_by_priority = {str(priority): count for priority, count in priority_result.all()}
        
        # Average processing time
        avg_time_stmt = select(func.avg(
            func.extract('epoch', Case.processing_completed_at - Case.processing_started_at)
        )).where(
            and_(
                Case.processing_started_at.is_not(None),
                Case.processing_completed_at.is_not(None)
            )
        )
        avg_time_result = await self.db.execute(avg_time_stmt)
        avg_processing_time = avg_time_result.scalar()
        
        # Active cases
        active_statuses = [CaseStatus.CREATED, CaseStatus.READY, CaseStatus.PROCESSING]
        active_stmt = select(func.count(Case.id)).where(Case.status.in_(active_statuses))
        active_result = await self.db.execute(active_stmt)
        active_cases = active_result.scalar()
        
        # Cases requiring review
        review_stmt = select(func.count(Case.id)).where(Case.status == CaseStatus.REVIEW_REQUIRED)
        review_result = await self.db.execute(review_stmt)
        cases_requiring_review = review_result.scalar()
        
        return {
            "total_cases": total_cases,
            "cases_by_status": cases_by_status,
            "cases_by_priority": cases_by_priority,
            "average_processing_time_seconds": avg_processing_time,
            "active_cases": active_cases,
            "cases_requiring_review": cases_requiring_review
        }
