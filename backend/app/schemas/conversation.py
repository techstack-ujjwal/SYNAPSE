"""Conversation-related schemas."""
from pydantic import BaseModel, Field


class ConversationIn(BaseModel):
    patient_id: str = ''
    message: str = Field(min_length=1, max_length=4000)
    language: str = 'English'
    history: list[dict] = []
