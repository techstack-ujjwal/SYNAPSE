"""Queue-related schemas."""
from pydantic import BaseModel


class QueueIn(BaseModel):
    patient_id: str
    priority: str = 'medium'
    symptoms: list[str] = []
