# DERCAS-ONCO-XAI V1 - Case Service Model Tests
# Unit tests for SQLAlchemy models

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from case_service.models import Patient, Case


class TestPatientModel:
    """Test Patient model functionality."""
    
    def test_patient_creation(self):
        """Test patient model creation."""
        patient = Patient(
            first_name="John",
            last_name="Doe",
            date_of_birth=datetime(1980, 1, 1),
            gender="M",
            medical_record_number="MRN123"
        )
        
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        assert patient.full_name == "John Doe"
        assert patient.gender == "M"
        assert patient.medical_record_number == "MRN123"
        assert patient.is_active is True
    
    def test_patient_age_calculation(self):
        """Test patient age calculation."""
        # Patient born 30 years ago
        birth_date = datetime.now() - timedelta(days=30*365)
        patient = Patient(
            first_name="Jane",
            last_name="Smith",
            date_of_birth=birth_date
        )
        
        age = patient.age
        assert age is not None
        assert 29 <= age <= 31  # Allow for some variance
    
    def test_patient_age_none_when_no_birth_date(self):
        """Test patient age is None when no birth date."""
        patient = Patient(
            first_name="John",
            last_name="Doe"
        )
        
        assert patient.age is None
    
    def test_patient_repr(self):
        """Test patient string representation."""
        patient = Patient(
            id="test-id",
            first_name="John",
            last_name="Doe"
        )
        
        repr_str = repr(patient)
        assert "Patient" in repr_str
        assert "test-id" in repr_str
        assert "John Doe" in repr_str


class TestCaseModel:
    """Test Case model functionality."""
    
    def test_case_creation(self):
        """Test case model creation."""
        case = Case(
            patient_id="patient-123",
            title="Test Case",
            description="Test description",
            status="draft",
            priority="normal"
        )
        
        assert case.patient_id == "patient-123"
        assert case.title == "Test Case"
        assert case.description == "Test description"
        assert case.status == "draft"
        assert case.priority == "normal"
        assert case.processing_status == "pending"
        assert case.processing_progress == 0
        assert case.is_active is True
    
    def test_case_processing_status_properties(self):
        """Test case processing status properties."""
        case = Case(
            patient_id="patient-123",
            title="Test Case",
            processing_status="pending"
        )
        
        assert not case.is_completed
        assert not case.is_processing
        assert not case.has_errors
        
        case.processing_status = "processing"
        assert not case.is_completed
        assert case.is_processing
        assert not case.has_errors
        
        case.processing_status = "completed"
        assert case.is_completed
        assert not case.is_processing
        assert not case.has_errors
        
        case.processing_status = "failed"
        assert not case.is_completed
        assert not case.is_processing
        assert case.has_errors
    
    def test_case_update_processing_status(self):
        """Test case processing status update."""
        case = Case(
            patient_id="patient-123",
            title="Test Case"
        )
        
        case.update_processing_status("processing", 50)
        assert case.processing_status == "processing"
        assert case.processing_progress == 50
        assert case.processing_error is None
        
        case.update_processing_status("failed", error="Test error")
        assert case.processing_status == "failed"
        assert case.processing_error == "Test error"
        
        case.update_processing_status("completed", 100)
        assert case.processing_status == "completed"
        assert case.processing_progress == 100
        assert case.processing_error is None
    
    def test_case_tag_management(self):
        """Test case tag management."""
        case = Case(
            patient_id="patient-123",
            title="Test Case"
        )
        
        # Add tags
        case.add_tag("lung cancer")
        case.add_tag("stage II")
        assert "lung cancer" in case.tags
        assert "stage II" in case.tags
        
        # Don't add duplicate tags
        case.add_tag("lung cancer")
        assert case.tags.count("lung cancer") == 1
        
        # Remove tag
        case.remove_tag("stage II")
        assert "stage II" not in case.tags
        assert "lung cancer" in case.tags
    
    def test_case_metadata_management(self):
        """Test case metadata management."""
        case = Case(
            patient_id="patient-123",
            title="Test Case"
        )
        
        # Set metadata
        case.set_metadata("tumor_size", "3.2cm")
        case.set_metadata("location", "right upper lobe")
        
        assert case.get_metadata("tumor_size") == "3.2cm"
        assert case.get_metadata("location") == "right upper lobe"
        assert case.get_metadata("nonexistent", "default") == "default"
    
    def test_case_repr(self):
        """Test case string representation."""
        case = Case(
            id="test-case-id",
            patient_id="patient-123",
            title="Test Case",
            status="active"
        )
        
        repr_str = repr(case)
        assert "Case" in repr_str
        assert "test-case-id" in repr_str
        assert "Test Case" in repr_str
        assert "active" in repr_str
