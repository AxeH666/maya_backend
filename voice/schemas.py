from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class VoiceRequest(BaseModel):
    """Request model for voice synthesis."""
    text: str
    voice_id: Optional[str] = None
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 1.0


class VoiceResponse(BaseModel):
    """Response model for voice operations."""
    job_id: str
    status: str  # "pending" | "processing" | "ready" | "failed"
    text: Optional[str] = None
    audio_url: Optional[str] = None


class VoiceJobStatus(BaseModel):
    """Status model for voice processing jobs."""
    job_id: str
    status: str  # "pending" | "processing" | "ready" | "failed"
    text: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class VoiceChatResponse(BaseModel):
    """
    Response model for voice chat API.
    
    Represents the complete response from a voice chat interaction,
    containing both the text reply from the LLM and the audio file
    URL for replaying the synthesized speech.
    
    This schema defines the API contract for voice chat responses.
    It does NOT include business logic, file handling, or API calls.
    """
    text: str = Field(..., min_length=1, description="The final text reply from the LLM")
    audio_url: str = Field(..., min_length=1, description="Relative URL to the generated audio file for replay")
    
    # Future extensibility placeholders (commented, not active fields):
    # agent_id: Optional[str] = None  # Identifier for the voice agent used
    # language: Optional[str] = None  # Language code (e.g., "en", "es", "fr")
    # voice_id: Optional[str] = None  # Voice identifier (e.g., "alloy", "echo", "fable")
    # duration_ms: Optional[int] = None  # Audio duration in milliseconds

