"""Report-related schemas."""
from pydantic import BaseModel
from typing import Optional


class SummaryIn(BaseModel):
    patient_id: str = ''
    form: dict = {}
    messages: list[dict] = []
    reports: list[dict] = []
    symptoms: list[str] = []
    language: str = 'English'
    report_data: dict = {}


class PrescriptionIn(BaseModel):
    patient_id: str
    visit_id: Optional[int] = None
    doctor_id: str
    doctor_notes: str = ''
    medications: list[dict] = []
    language: str = 'English'
