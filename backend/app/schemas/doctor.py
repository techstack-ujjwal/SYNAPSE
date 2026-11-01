"""Doctor-related schemas."""
from pydantic import BaseModel, Field


class DoctorIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    specialty: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r'^(?:\+91[6-9]\d{9}|[6-9]\d{9})$')
    is_active: bool = True
