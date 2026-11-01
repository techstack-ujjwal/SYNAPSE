"""
Characterisation tests for existing backend endpoints.

These tests document the current behavior of main.py endpoints.
They ensure that when we refactor/split the code, behavior doesn't change.
"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory to path to import main
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the existing main app (before refactoring)
from main import app

client = TestClient(app)


class TestPatientEndpoints:
    """Test patient-related endpoints."""

    def test_create_patient(self):
        """Test creating a new patient."""
        response = client.post(
            "/patients",
            json={
                "name": "Test Patient",
                "age": 30,
                "phone": "9876543210",
                "sex": "Male",
                "vitals": {}
            }
        )
        # Document current behavior
        assert response.status_code in [200, 201]  # May be 200 or 201
        data = response.json()
        assert "patient_id" in data or "id" in data

    def test_get_patient(self):
        """Test getting a patient by ID."""
        # Document: GET endpoint doesn't exist in current main.py
        # Will need to be added during refactoring
        pass


class TestDoctorEndpoints:
    """Test doctor-related endpoints."""

    def test_create_doctor(self):
        """Test creating a new doctor."""
        # Document: /doctors is GET only, no POST endpoint exists
        # Doctors are seeded in seed_doctors() function
        pass

    def test_get_doctors(self):
        """Test getting all doctors."""
        response = client.get("/doctors")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Document: currently returns phone numbers (B-18)


class TestConversationEndpoints:
    """Test conversation endpoints."""

    def test_conversation(self):
        """Test the conversation endpoint."""
        # Document: /conversation endpoint doesn't exist
        # Conversation is handled by different endpoints in current implementation
        pass


class TestQueueEndpoints:
    """Test queue-related endpoints."""

    def test_add_to_queue(self):
        """Test adding a patient to queue."""
        response = client.post(
            "/queue",
            json={
                "patient_id": "test-patient",
                "priority": "medium",
                "symptoms": ["headache"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data or "queue_id" in data

    def test_get_queue(self):
        """Test getting the queue."""
        response = client.get("/queue")
        assert response.status_code == 200
        data = response.json()
        # Document: currently returns dict, not list
        # Structure: {'people_ahead': 1, 'estimated_minutes': 12, 'next_token': 2, 'prefix': 'S'}
        assert isinstance(data, dict)


class TestReportEndpoints:
    """Test report-related endpoints."""

    def test_upload_report(self):
        """Test uploading a report."""
        # Document: /upload-report endpoint doesn't exist
        # Report upload is handled by different endpoint
        pass


class TestSummaryEndpoint:
    """Test summary generation endpoint."""

    def test_summary(self):
        """Test generating a summary."""
        response = client.post(
            "/summary",
            json={
                "patient_id": "test-patient",
                "form": {},
                "messages": [],
                "reports": [],
                "symptoms": ["headache"],
                "language": "English",
                "report_data": {}
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Document: currently has hardcoded fallback with "None reported" (B-08)
        assert "summary" in data or "text" in data


class TestPriorityEndpoint:
    """Test AI priority determination endpoint."""

    def test_ai_determine_priority(self):
        """Test AI priority determination."""
        # Document: /ai-determine-priority endpoint doesn't exist
        # Priority is calculated in calculate_priority() function
        pass


class TestSpecialtyMatching:
    """Test specialty matching logic."""

    def test_specialty_matching(self):
        """Test that specialty matching works."""
        # This tests the match_doctor_specialty function
        # Document: currently uses substring matching (B-05)
        # Example: 'kid' matches 'kidney' → routes to Paediatrics incorrectly
        pass  # Will test this after extracting the function


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
