# DERCAS-ONCO-XAI V1 - Case Service Seed Data
# Basic seed data for development and testing

from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from .models import Patient, Case
from .crud import PatientCRUD, CaseCRUD
from .schemas import PatientCreate, CaseCreate, GenderEnum, CaseStatusEnum, CasePriorityEnum

logger = structlog.get_logger(__name__)


class SeedDataManager:
    """Manager for seeding development and test data."""
    
    def __init__(self):
        self.patients_data = self._get_sample_patients()
        self.cases_data = self._get_sample_cases()
    
    def _get_sample_patients(self) -> List[PatientCreate]:
        """Get sample patient data."""
        base_date = datetime.now() - timedelta(days=365)
        
        return [
            PatientCreate(
                external_id="EXT001",
                first_name="John",
                last_name="Smith",
                date_of_birth=datetime(1965, 3, 15),
                gender=GenderEnum.MALE,
                medical_record_number="MRN001234",
                metadata_={
                    "insurance": "Blue Cross",
                    "emergency_contact": "Jane Smith",
                    "allergies": ["Penicillin"]
                }
            ),
            PatientCreate(
                external_id="EXT002",
                first_name="Maria",
                last_name="Garcia",
                date_of_birth=datetime(1972, 8, 22),
                gender=GenderEnum.FEMALE,
                medical_record_number="MRN005678",
                metadata_={
                    "insurance": "Aetna",
                    "emergency_contact": "Carlos Garcia",
                    "allergies": []
                }
            ),
            PatientCreate(
                external_id="EXT003",
                first_name="Robert",
                last_name="Johnson",
                date_of_birth=datetime(1958, 11, 8),
                gender=GenderEnum.MALE,
                medical_record_number="MRN009876",
                metadata_={
                    "insurance": "Medicare",
                    "emergency_contact": "Susan Johnson",
                    "allergies": ["Sulfa drugs"]
                }
            ),
            PatientCreate(
                external_id="EXT004",
                first_name="Lisa",
                last_name="Chen",
                date_of_birth=datetime(1980, 5, 12),
                gender=GenderEnum.FEMALE,
                medical_record_number="MRN112233",
                metadata_={
                    "insurance": "Kaiser Permanente",
                    "emergency_contact": "David Chen",
                    "allergies": ["Latex"]
                }
            ),
            PatientCreate(
                external_id="EXT005",
                first_name="Michael",
                last_name="Brown",
                date_of_birth=datetime(1963, 9, 30),
                gender=GenderEnum.MALE,
                medical_record_number="MRN445566",
                metadata_={
                    "insurance": "United Healthcare",
                    "emergency_contact": "Patricia Brown",
                    "allergies": ["Iodine"]
                }
            ),
            PatientCreate(
                first_name="Sarah",
                last_name="Wilson",
                date_of_birth=datetime(1975, 2, 18),
                gender=GenderEnum.FEMALE,
                medical_record_number="MRN778899",
                metadata_={
                    "insurance": "Cigna",
                    "emergency_contact": "James Wilson",
                    "allergies": []
                }
            ),
            PatientCreate(
                first_name="David",
                last_name="Lee",
                date_of_birth=datetime(1969, 7, 25),
                gender=GenderEnum.MALE,
                medical_record_number="MRN334455",
                metadata_={
                    "insurance": "Humana",
                    "emergency_contact": "Jennifer Lee",
                    "allergies": ["Aspirin"]
                }
            ),
            PatientCreate(
                first_name="Jennifer",
                last_name="Taylor",
                date_of_birth=datetime(1982, 12, 3),
                gender=GenderEnum.FEMALE,
                medical_record_number="MRN667788",
                metadata_={
                    "insurance": "Blue Shield",
                    "emergency_contact": "Mark Taylor",
                    "allergies": ["Shellfish"]
                }
            )
        ]
    
    def _get_sample_cases(self) -> List[dict]:
        """Get sample case data (will be created after patients)."""
        base_date = datetime.now() - timedelta(days=180)
        
        return [
            {
                "patient_index": 0,  # John Smith
                "case_data": CaseCreate(
                    patient_id="",  # Will be filled after patient creation
                    external_id="CASE001",
                    title="Suspected Lung Adenocarcinoma - Right Upper Lobe",
                    description="68-year-old male with 40-pack-year smoking history presenting with persistent cough and weight loss. CT scan shows 3.2cm mass in right upper lobe with mediastinal lymphadenopathy.",
                    status=CaseStatusEnum.ACTIVE,
                    priority=CasePriorityEnum.HIGH,
                    diagnosis="Suspected lung adenocarcinoma",
                    clinical_notes="Patient reports 3-month history of productive cough with occasional hemoptysis. 15-pound weight loss over 2 months. Performance status ECOG 1.",
                    case_date=base_date + timedelta(days=1),
                    admission_date=base_date + timedelta(days=1),
                    tags=["lung cancer", "adenocarcinoma", "smoking history"],
                    metadata_={
                        "smoking_history": "40 pack-years",
                        "performance_status": "ECOG 1",
                        "tumor_size": "3.2cm",
                        "location": "right upper lobe"
                    }
                )
            },
            {
                "patient_index": 1,  # Maria Garcia
                "case_data": CaseCreate(
                    patient_id="",
                    external_id="CASE002",
                    title="Lung Nodule Evaluation - Left Lower Lobe",
                    description="52-year-old female non-smoker with incidental finding of 1.8cm nodule on routine chest CT. Family history of lung cancer.",
                    status=CaseStatusEnum.ACTIVE,
                    priority=CasePriorityEnum.NORMAL,
                    diagnosis="Pulmonary nodule, indeterminate",
                    clinical_notes="Asymptomatic patient. Nodule discovered on routine screening. No respiratory symptoms. Family history significant for maternal lung cancer.",
                    case_date=base_date + timedelta(days=15),
                    admission_date=base_date + timedelta(days=15),
                    tags=["lung nodule", "screening", "family history"],
                    metadata_={
                        "smoking_history": "never smoker",
                        "family_history": "maternal lung cancer",
                        "nodule_size": "1.8cm",
                        "location": "left lower lobe"
                    }
                )
            },
            {
                "patient_index": 2,  # Robert Johnson
                "case_data": CaseCreate(
                    patient_id="",
                    external_id="CASE003",
                    title="Advanced NSCLC with Brain Metastases",
                    description="66-year-old male with stage IV non-small cell lung cancer and newly diagnosed brain metastases. Currently on palliative care.",
                    status=CaseStatusEnum.COMPLETED,
                    priority=CasePriorityEnum.URGENT,
                    diagnosis="Stage IV NSCLC with brain metastases",
                    clinical_notes="Patient with known stage IV NSCLC now presenting with neurological symptoms. MRI brain shows multiple metastatic lesions. Discussing palliative radiation therapy.",
                    case_date=base_date + timedelta(days=30),
                    admission_date=base_date + timedelta(days=30),
                    discharge_date=base_date + timedelta(days=37),
                    tags=["NSCLC", "stage IV", "brain metastases", "palliative"],
                    metadata_={
                        "stage": "IV",
                        "metastases": ["brain", "liver"],
                        "treatment_intent": "palliative",
                        "performance_status": "ECOG 3"
                    }
                )
            },
            {
                "patient_index": 3,  # Lisa Chen
                "case_data": CaseCreate(
                    patient_id="",
                    title="Early Stage Lung Cancer - Surgical Candidate",
                    description="44-year-old female non-smoker with early-stage lung adenocarcinoma. Candidate for surgical resection.",
                    status=CaseStatusEnum.ACTIVE,
                    priority=CasePriorityEnum.HIGH,
                    diagnosis="T1N0M0 lung adenocarcinoma",
                    clinical_notes="Young non-smoking female with early-stage disease. Excellent surgical candidate. PET scan shows no evidence of distant metastases.",
                    case_date=base_date + timedelta(days=45),
                    admission_date=base_date + timedelta(days=45),
                    tags=["early stage", "surgical candidate", "non-smoker", "young"],
                    metadata_={
                        "stage": "IA",
                        "smoking_history": "never smoker",
                        "surgical_plan": "VATS lobectomy",
                        "performance_status": "ECOG 0"
                    }
                )
            },
            {
                "patient_index": 4,  # Michael Brown
                "case_data": CaseCreate(
                    patient_id="",
                    title="Recurrent Lung Cancer - Immunotherapy Response",
                    description="61-year-old male with recurrent lung cancer showing excellent response to immunotherapy. Regular follow-up for monitoring.",
                    status=CaseStatusEnum.ACTIVE,
                    priority=CasePriorityEnum.NORMAL,
                    diagnosis="Recurrent lung adenocarcinoma",
                    clinical_notes="Patient with history of resected lung cancer now with recurrence. Started on pembrolizumab with excellent radiographic response. Tolerating treatment well.",
                    case_date=base_date + timedelta(days=60),
                    tags=["recurrent", "immunotherapy", "pembrolizumab", "response"],
                    metadata_={
                        "treatment": "pembrolizumab",
                        "response": "partial response",
                        "cycles_completed": 8,
                        "toxicity": "grade 1 fatigue"
                    }
                )
            },
            {
                "patient_index": 5,  # Sarah Wilson
                "case_data": CaseCreate(
                    patient_id="",
                    title="Lung Cancer Screening - High Risk Patient",
                    description="49-year-old female with significant smoking history undergoing lung cancer screening. Multiple small nodules detected.",
                    status=CaseStatusEnum.DRAFT,
                    priority=CasePriorityEnum.LOW,
                    clinical_notes="High-risk patient for lung cancer screening. Multiple small nodules (<6mm) detected. Recommend follow-up CT in 6 months.",
                    case_date=base_date + timedelta(days=75),
                    tags=["screening", "high risk", "multiple nodules"],
                    metadata_={
                        "smoking_history": "30 pack-years",
                        "nodule_count": 4,
                        "largest_nodule": "5mm",
                        "recommendation": "6-month follow-up"
                    }
                )
            },
            {
                "patient_index": 6,  # David Lee
                "case_data": CaseCreate(
                    patient_id="",
                    title="Lung Cancer Molecular Testing - EGFR Mutation",
                    description="55-year-old male with lung adenocarcinoma positive for EGFR mutation. Candidate for targeted therapy.",
                    status=CaseStatusEnum.ACTIVE,
                    priority=CasePriorityEnum.HIGH,
                    diagnosis="EGFR-positive lung adenocarcinoma",
                    clinical_notes="Molecular testing reveals EGFR exon 19 deletion. Patient is candidate for first-line EGFR TKI therapy. Discussing treatment options.",
                    case_date=base_date + timedelta(days=90),
                    tags=["EGFR mutation", "targeted therapy", "molecular testing"],
                    metadata_={
                        "mutation": "EGFR exon 19 deletion",
                        "treatment_plan": "osimertinib",
                        "stage": "IIIA",
                        "performance_status": "ECOG 1"
                    }
                )
            },
            {
                "patient_index": 7,  # Jennifer Taylor
                "case_data": CaseCreate(
                    patient_id="",
                    title="Young Adult Lung Cancer - Rare Presentation",
                    description="42-year-old female non-smoker with lung adenocarcinoma. Investigating potential genetic predisposition.",
                    status=CaseStatusEnum.ACTIVE,
                    priority=CasePriorityEnum.HIGH,
                    diagnosis="Lung adenocarcinoma in young adult",
                    clinical_notes="Unusual presentation of lung cancer in young non-smoking female. Genetic counseling recommended. Investigating family history and potential hereditary factors.",
                    case_date=base_date + timedelta(days=105),
                    tags=["young adult", "non-smoker", "genetic counseling", "rare"],
                    metadata_={
                        "age_at_diagnosis": 42,
                        "smoking_history": "never smoker",
                        "genetic_testing": "pending",
                        "family_history": "negative"
                    }
                )
            }
        ]
    
    async def seed_patients(self, db: AsyncSession, created_by: str = "system") -> List[Patient]:
        """
        Seed patient data.
        
        Args:
            db: Database session
            created_by: User creating the data
            
        Returns:
            List of created patients
        """
        patients = []
        
        for patient_data in self.patients_data:
            try:
                # Check if patient already exists
                existing_patient = None
                if patient_data.external_id:
                    existing_patient = await PatientCRUD.get_by_external_id(db, patient_data.external_id)
                
                if not existing_patient and patient_data.medical_record_number:
                    existing_patient = await PatientCRUD.get_by_mrn(db, patient_data.medical_record_number)
                
                if existing_patient:
                    logger.info(
                        "Patient already exists, skipping",
                        patient_name=f"{patient_data.first_name} {patient_data.last_name}",
                        existing_id=existing_patient.id
                    )
                    patients.append(existing_patient)
                    continue
                
                # Create patient
                patient = await PatientCRUD.create(db, patient_data, created_by)
                patients.append(patient)
                
                logger.info(
                    "Patient seeded",
                    patient_id=patient.id,
                    patient_name=patient.full_name
                )
                
            except Exception as e:
                logger.error(
                    "Failed to seed patient",
                    patient_name=f"{patient_data.first_name} {patient_data.last_name}",
                    error=str(e)
                )
                continue
        
        await db.commit()
        logger.info(f"Seeded {len(patients)} patients")
        return patients
    
    async def seed_cases(self, db: AsyncSession, patients: List[Patient], created_by: str = "system") -> List[Case]:
        """
        Seed case data.
        
        Args:
            db: Database session
            patients: List of created patients
            created_by: User creating the data
            
        Returns:
            List of created cases
        """
        cases = []
        
        for case_info in self.cases_data:
            try:
                patient_index = case_info["patient_index"]
                case_data = case_info["case_data"]
                
                if patient_index >= len(patients):
                    logger.warning(
                        "Patient index out of range, skipping case",
                        patient_index=patient_index,
                        case_title=case_data.title
                    )
                    continue
                
                # Set patient ID
                case_data.patient_id = patients[patient_index].id
                
                # Check if case already exists
                existing_case = None
                if case_data.external_id:
                    existing_case = await CaseCRUD.get_by_external_id(db, case_data.external_id)
                
                if existing_case:
                    logger.info(
                        "Case already exists, skipping",
                        case_title=case_data.title,
                        existing_id=existing_case.id
                    )
                    cases.append(existing_case)
                    continue
                
                # Create case
                case = await CaseCRUD.create(db, case_data, created_by)
                cases.append(case)
                
                logger.info(
                    "Case seeded",
                    case_id=case.id,
                    case_title=case.title,
                    patient_id=case.patient_id
                )
                
            except Exception as e:
                logger.error(
                    "Failed to seed case",
                    case_title=case_data.title if 'case_data' in locals() else "unknown",
                    error=str(e)
                )
                continue
        
        await db.commit()
        logger.info(f"Seeded {len(cases)} cases")
        return cases
    
    async def seed_all(self, db: AsyncSession, created_by: str = "system") -> dict:
        """
        Seed all data.
        
        Args:
            db: Database session
            created_by: User creating the data
            
        Returns:
            Dictionary with seeded data counts
        """
        logger.info("Starting seed data creation")
        
        # Seed patients first
        patients = await self.seed_patients(db, created_by)
        
        # Seed cases
        cases = await self.seed_cases(db, patients, created_by)
        
        result = {
            "patients_created": len(patients),
            "cases_created": len(cases),
            "total_records": len(patients) + len(cases)
        }
        
        logger.info(
            "Seed data creation completed",
            **result
        )
        
        return result
    
    async def clear_all_data(self, db: AsyncSession) -> dict:
        """
        Clear all seeded data (for testing).
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with cleared data counts
        """
        logger.warning("Clearing all seed data")
        
        # This would typically be used only in test environments
        from sqlalchemy import delete
        
        # Delete cases first (due to foreign key constraint)
        cases_result = await db.execute(delete(Case))
        cases_deleted = cases_result.rowcount
        
        # Delete patients
        patients_result = await db.execute(delete(Patient))
        patients_deleted = patients_result.rowcount
        
        await db.commit()
        
        result = {
            "patients_deleted": patients_deleted,
            "cases_deleted": cases_deleted,
            "total_deleted": patients_deleted + cases_deleted
        }
        
        logger.warning(
            "All seed data cleared",
            **result
        )
        
        return result


async def seed_database(db: AsyncSession, created_by: str = "system") -> dict:
    """
    Convenience function to seed the database.
    
    Args:
        db: Database session
        created_by: User creating the data
        
    Returns:
        Dictionary with seeded data counts
    """
    seed_manager = SeedDataManager()
    return await seed_manager.seed_all(db, created_by)


async def clear_database(db: AsyncSession) -> dict:
    """
    Convenience function to clear the database (for testing).
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with cleared data counts
    """
    seed_manager = SeedDataManager()
    return await seed_manager.clear_all_data(db)
