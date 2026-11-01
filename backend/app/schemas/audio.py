"""Audio-related schemas."""
from pydantic import BaseModel


class AudioTranscribeIn(BaseModel):
    audio_data: str  # Base64 encoded audio
    language: str = 'English'


class TextToSpeechIn(BaseModel):
    text: str
    language: str = 'English'
    voice: str = 'nova'  # nova, shimmer, alloy, echo, fable, onyx
