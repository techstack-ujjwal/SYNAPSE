"""Additional report-related schemas."""
from pydantic import BaseModel


class ReportComparisonIn(BaseModel):
    patient_id: str
    past_report_id: int
    present_report_id: int
    language: str = 'English'


class HandwrittenReportIn(BaseModel):
    patient_id: str
    language: str = 'English'


class GenerateReportIn(BaseModel):
    patient_id: str
    doctor_id: str
    doctor_notes: str = ''
    medications: list[dict] = []
    diagnosis: str = ''
    language: str = 'English'


class ReassignDoctorIn(BaseModel):
    patient_id: str
    new_doctor_id: str


class CompleteConsultationIn(BaseModel):
    patient_id: str
