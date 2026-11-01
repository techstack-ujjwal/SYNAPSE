"""Patient-related schemas."""
from pydantic import BaseModel, Field


class PatientIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    age: int = Field(ge=0, le=120)
    phone: str = Field(pattern=r'^(?:\+91[6-9]\d{9}|[6-9]\d{9})$')
    sex: str = Field(min_length=1)
    vitals: dict = {}
