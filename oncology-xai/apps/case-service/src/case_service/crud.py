# DERCAS-ONCO-XAI V1 - Case Service CRUD Operations
# Database CRUD operations for patients and cases

from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from .models import Patient, Case
from .schemas import (
    PatientCreate, PatientUpdate, PatientFilters,
    CaseCreate, CaseUpdate, CaseFilters,
    PaginationParams
)

logger = structlog.get_logger(__name__)


class PatientCRUD:
    """CRUD operations for Patient model."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        patient_data: PatientCreate,
        created_by: Optional[str] = None
    ) -> Patient:
        """
        Create a new patient.
        
        Args:
            db: Database session
            patient_data: Patient creation data
            created_by: User creating the patient
            
        Returns:
            Created patient
        """
        patient = Patient(
            external_id=patient_data.external_id,
            first_name=patient_data.first_name,
            last_name=patient_data.last_name,
            date_of_birth=patient_data.date_of_birth,
            gender=patient_data.gender,
            medical_record_number=patient_data.medical_record_number,
            metadata_=patient_data.metadata_,
            created_by=created_by,
            updated_by=created_by
        )
        
        db.add(patient)
        await db.flush()
        await db.refresh(patient)
        
        logger.info(
            "Patient created",
            patient_id=patient.id,
            name=patient.full_name,
            created_by=created_by
        )
        
        return patient
    
    @staticmethod
    async def get_by_id(db: AsyncSession, patient_id: str) -> Optional[Patient]:
        """
        Get patient by ID.
        
        Args:
            db: Database session
            patient_id: Patient ID
            
        Returns:
            Patient or None
        """
        result = await db.execute(
            select(Patient)
            .options(selectinload(Patient.cases))
            .where(and_(Patient.id == patient_id, Patient.is_active == True))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_external_id(db: AsyncSession, external_id: str) -> Optional[Patient]:
        """
        Get patient by external ID.
        
        Args:
            db: Database session
            external_id: External patient ID
            
        Returns:
            Patient or None
        """
        result = await db.execute(
            select(Patient)
            .where(and_(
                Patient.external_id == external_id,
                Patient.is_active == True
            ))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_mrn(db: AsyncSession, mrn: str) -> Optional[Patient]:
        """
        Get patient by medical record number.
        
        Args:
            db: Database session
            mrn: Medical record number
            
        Returns:
            Patient or None
        """
        result = await db.execute(
            select(Patient)
            .where(and_(
                Patient.medical_record_number == mrn,
                Patient.is_active == True
            ))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_patients(
        db: AsyncSession,
        pagination: PaginationParams,
        filters: Optional[PatientFilters] = None,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Patient], int]:
        """
        List patients with pagination and filtering.
        
        Args:
            db: Database session
            pagination: Pagination parameters
            filters: Filter parameters
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            Tuple of (patients, total_count)
        """
        # Build base query
        query = select(Patient).where(Patient.is_active == True)
        count_query = select(func.count(Patient.id)).where(Patient.is_active == True)
        
        # Apply filters
        if filters:
            conditions = []
            
            if filters.search:
                search_term = f"%{filters.search}%"
                conditions.append(
                    or_(
                        Patient.first_name.ilike(search_term),
                        Patient.last_name.ilike(search_term),
                        Patient.medical_record_number.ilike(search_term)
                    )
                )
            
            if filters.gender:
                conditions.append(Patient.gender == filters.gender)
            
            if filters.created_after:
                conditions.append(Patient.created_at >= filters.created_after)
            
            if filters.created_before:
                conditions.append(Patient.created_at <= filters.created_before)
            
            if filters.is_active is not None:
                conditions.append(Patient.is_active == filters.is_active)
            
            if conditions:
                filter_condition = and_(*conditions)
                query = query.where(filter_condition)
                count_query = count_query.where(filter_condition)
        
        # Apply ordering
        order_column = getattr(Patient, order_by, Patient.created_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.size)
        
        # Execute queries
        result = await db.execute(query)
        patients = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        return list(patients), total_count
    
    @staticmethod
    async def update(
        db: AsyncSession,
        patient: Patient,
        patient_data: PatientUpdate,
        updated_by: Optional[str] = None
    ) -> Patient:
        """
        Update patient.
        
        Args:
            db: Database session
            patient: Patient to update
            patient_data: Update data
            updated_by: User updating the patient
            
        Returns:
            Updated patient
        """
        update_data = patient_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "metadata_":
                field = "metadata_"
            setattr(patient, field, value)
        
        patient.updated_by = updated_by
        patient.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(patient)
        
        logger.info(
            "Patient updated",
            patient_id=patient.id,
            updated_by=updated_by
        )
        
        return patient
    
    @staticmethod
    async def delete(
        db: AsyncSession,
        patient: Patient,
        deleted_by: Optional[str] = None
    ) -> Patient:
        """
        Soft delete patient.
        
        Args:
            db: Database session
            patient: Patient to delete
            deleted_by: User deleting the patient
            
        Returns:
            Deleted patient
        """
        patient.is_active = False
        patient.updated_by = deleted_by
        patient.updated_at = datetime.utcnow()
        
        await db.flush()
        
        logger.info(
            "Patient deleted",
            patient_id=patient.id,
            deleted_by=deleted_by
        )
        
        return patient


class CaseCRUD:
    """CRUD operations for Case model."""
    
    @staticmethod
    async def create(
        db: AsyncSession,
        case_data: CaseCreate,
        created_by: Optional[str] = None
    ) -> Case:
        """
        Create a new case.
        
        Args:
            db: Database session
            case_data: Case creation data
            created_by: User creating the case
            
        Returns:
            Created case
        """
        case = Case(
            patient_id=case_data.patient_id,
            external_id=case_data.external_id,
            title=case_data.title,
            description=case_data.description,
            status=case_data.status,
            priority=case_data.priority,
            diagnosis=case_data.diagnosis,
            clinical_notes=case_data.clinical_notes,
            case_date=case_data.case_date,
            admission_date=case_data.admission_date,
            discharge_date=case_data.discharge_date,
            tags=case_data.tags,
            metadata_=case_data.metadata_,
            created_by=created_by,
            updated_by=created_by
        )
        
        db.add(case)
        await db.flush()
        await db.refresh(case, ["patient"])
        
        logger.info(
            "Case created",
            case_id=case.id,
            patient_id=case.patient_id,
            title=case.title,
            created_by=created_by
        )
        
        return case
    
    @staticmethod
    async def get_by_id(db: AsyncSession, case_id: str) -> Optional[Case]:
        """
        Get case by ID.
        
        Args:
            db: Database session
            case_id: Case ID
            
        Returns:
            Case or None
        """
        result = await db.execute(
            select(Case)
            .options(selectinload(Case.patient))
            .where(and_(Case.id == case_id, Case.is_active == True))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_external_id(db: AsyncSession, external_id: str) -> Optional[Case]:
        """
        Get case by external ID.
        
        Args:
            db: Database session
            external_id: External case ID
            
        Returns:
            Case or None
        """
        result = await db.execute(
            select(Case)
            .options(selectinload(Case.patient))
            .where(and_(
                Case.external_id == external_id,
                Case.is_active == True
            ))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_cases(
        db: AsyncSession,
        pagination: PaginationParams,
        filters: Optional[CaseFilters] = None,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Case], int]:
        """
        List cases with pagination and filtering.
        
        Args:
            db: Database session
            pagination: Pagination parameters
            filters: Filter parameters
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            Tuple of (cases, total_count)
        """
        # Build base query
        query = select(Case).options(selectinload(Case.patient)).where(Case.is_active == True)
        count_query = select(func.count(Case.id)).where(Case.is_active == True)
        
        # Apply filters
        if filters:
            conditions = []
            
            if filters.search:
                search_term = f"%{filters.search}%"
                conditions.append(
                    or_(
                        Case.title.ilike(search_term),
                        Case.description.ilike(search_term),
                        Case.diagnosis.ilike(search_term)
                    )
                )
            
            if filters.patient_id:
                conditions.append(Case.patient_id == filters.patient_id)
            
            if filters.status:
                conditions.append(Case.status == filters.status)
            
            if filters.priority:
                conditions.append(Case.priority == filters.priority)
            
            if filters.processing_status:
                conditions.append(Case.processing_status == filters.processing_status)
            
            if filters.has_images is not None:
                conditions.append(Case.has_images == filters.has_images)
            
            if filters.has_inference_results is not None:
                conditions.append(Case.has_inference_results == filters.has_inference_results)
            
            if filters.case_date_after:
                conditions.append(Case.case_date >= filters.case_date_after)
            
            if filters.case_date_before:
                conditions.append(Case.case_date <= filters.case_date_before)
            
            if filters.created_after:
                conditions.append(Case.created_at >= filters.created_after)
            
            if filters.created_before:
                conditions.append(Case.created_at <= filters.created_before)
            
            if filters.tags:
                # Filter by tags (JSONB contains)
                for tag in filters.tags:
                    conditions.append(Case.tags.contains([tag]))
            
            if filters.is_active is not None:
                conditions.append(Case.is_active == filters.is_active)
            
            if conditions:
                filter_condition = and_(*conditions)
                query = query.where(filter_condition)
                count_query = count_query.where(filter_condition)
        
        # Apply ordering
        order_column = getattr(Case, order_by, Case.created_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.size)
        
        # Execute queries
        result = await db.execute(query)
        cases = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        return list(cases), total_count
    
    @staticmethod
    async def list_cases_by_patient(
        db: AsyncSession,
        patient_id: str,
        pagination: PaginationParams,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Case], int]:
        """
        List cases for a specific patient.
        
        Args:
            db: Database session
            patient_id: Patient ID
            pagination: Pagination parameters
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            Tuple of (cases, total_count)
        """
        # Build query
        query = select(Case).where(
            and_(
                Case.patient_id == patient_id,
                Case.is_active == True
            )
        )
        count_query = select(func.count(Case.id)).where(
            and_(
                Case.patient_id == patient_id,
                Case.is_active == True
            )
        )
        
        # Apply ordering
        order_column = getattr(Case, order_by, Case.created_at)
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.size)
        
        # Execute queries
        result = await db.execute(query)
        cases = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        return list(cases), total_count
    
    @staticmethod
    async def update(
        db: AsyncSession,
        case: Case,
        case_data: CaseUpdate,
        updated_by: Optional[str] = None
    ) -> Case:
        """
        Update case.
        
        Args:
            db: Database session
            case: Case to update
            case_data: Update data
            updated_by: User updating the case
            
        Returns:
            Updated case
        """
        update_data = case_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "metadata_":
                field = "metadata_"
            setattr(case, field, value)
        
        case.updated_by = updated_by
        case.updated_at = datetime.utcnow()
        
        await db.flush()
        await db.refresh(case, ["patient"])
        
        logger.info(
            "Case updated",
            case_id=case.id,
            updated_by=updated_by
        )
        
        return case
    
    @staticmethod
    async def update_processing_status(
        db: AsyncSession,
        case: Case,
        status: str,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Case:
        """
        Update case processing status.
        
        Args:
            db: Database session
            case: Case to update
            status: Processing status
            progress: Processing progress (0-100)
            error: Error message if failed
            updated_by: User updating the case
            
        Returns:
            Updated case
        """
        case.update_processing_status(status, progress, error)
        case.updated_by = updated_by
        case.updated_at = datetime.utcnow()
        
        await db.flush()
        
        logger.info(
            "Case processing status updated",
            case_id=case.id,
            status=status,
            progress=progress,
            updated_by=updated_by
        )
        
        return case
    
    @staticmethod
    async def delete(
        db: AsyncSession,
        case: Case,
        deleted_by: Optional[str] = None
    ) -> Case:
        """
        Soft delete case.
        
        Args:
            db: Database session
            case: Case to delete
            deleted_by: User deleting the case
            
        Returns:
            Deleted case
        """
        case.is_active = False
        case.updated_by = deleted_by
        case.updated_at = datetime.utcnow()
        
        await db.flush()
        
        logger.info(
            "Case deleted",
            case_id=case.id,
            deleted_by=deleted_by
        )
        
        return case
    
    @staticmethod
    async def get_case_statistics(db: AsyncSession) -> Dict[str, Any]:
        """
        Get case statistics.
        
        Args:
            db: Database session
            
        Returns:
            Statistics dictionary
        """
        # Total cases
        total_result = await db.execute(
            select(func.count(Case.id)).where(Case.is_active == True)
        )
        total_cases = total_result.scalar()
        
        # Cases by status
        status_result = await db.execute(
            select(Case.status, func.count(Case.id))
            .where(Case.is_active == True)
            .group_by(Case.status)
        )
        status_counts = dict(status_result.all())
        
        # Cases by processing status
        processing_result = await db.execute(
            select(Case.processing_status, func.count(Case.id))
            .where(Case.is_active == True)
            .group_by(Case.processing_status)
        )
        processing_counts = dict(processing_result.all())
        
        # Cases with data
        data_result = await db.execute(
            select(
                func.count(Case.id).filter(Case.has_images == True).label("with_images"),
                func.count(Case.id).filter(Case.has_ehr_data == True).label("with_ehr"),
                func.count(Case.id).filter(Case.has_inference_results == True).label("with_inference"),
                func.count(Case.id).filter(Case.has_graph_data == True).label("with_graph")
            )
            .where(Case.is_active == True)
        )
        data_counts = data_result.first()
        
        return {
            "total_cases": total_cases,
            "by_status": status_counts,
            "by_processing_status": processing_counts,
            "with_images": data_counts.with_images,
            "with_ehr_data": data_counts.with_ehr,
            "with_inference_results": data_counts.with_inference,
            "with_graph_data": data_counts.with_graph
        }
