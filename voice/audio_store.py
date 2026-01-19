"""
Centralized audio job tracking and state management.

This module maintains an in-memory store of all audio jobs,
handling state transitions and providing a single source of truth.
Also provides utilities for audio file storage.
"""
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Audio storage directory
AUDIO_DIR = Path(__file__).parent.parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job store
# TODO: Replace with database in production
_JOBS: Dict[str, dict] = {}


def create_job(job_id: str, job_type: str, user_id: Optional[str] = None) -> dict:
    """
    Create a new job with pending status.
    
    Args:
        job_id: Unique job identifier
        job_type: Type of job ("stt" | "tts")
        user_id: Optional user identifier if authenticated
        
    Returns:
        dict: The newly created job
    """
    job = {
        "job_id": job_id,
        "status": "pending",
        "job_type": job_type,
        "text": None,
        "audio_url": None,
        "created_at": datetime.now(),
        "updated_at": None,
        "user_id": user_id
    }
    _JOBS[job_id] = job
    return job


def get_job(job_id: str) -> Optional[dict]:
    """
    Retrieve a job by ID.
    
    Args:
        job_id: The job identifier
        
    Returns:
        dict if found, None otherwise
    """
    return _JOBS.get(job_id)


def update_job_status(
    job_id: str,
    status: str,
    text: Optional[str] = None,
    audio_url: Optional[str] = None
) -> bool:
    """
    Update job status and optionally text/audio_url.
    Handles state transitions: pending → processing → ready/failed
    
    Args:
        job_id: The job identifier
        status: New status ("pending" | "processing" | "ready" | "failed")
        text: Optional transcribed text (for STT) or source text (for TTS)
        audio_url: Optional audio URL when status is "ready"
        
    Returns:
        True if update succeeded, False if job not found
    """
    if job_id not in _JOBS:
        return False
    
    job = _JOBS[job_id]
    job["status"] = status
    job["updated_at"] = datetime.now()
    if text is not None:
        job["text"] = text
    if audio_url is not None:
        job["audio_url"] = audio_url
    
    return True


def mark_job_processing(job_id: str) -> bool:
    """Transition job from pending to processing."""
    return update_job_status(job_id, "processing")


def mark_job_ready(job_id: str, text: Optional[str] = None, audio_url: Optional[str] = None) -> bool:
    """Transition job to ready status with optional text and audio URL."""
    return update_job_status(job_id, "ready", text=text, audio_url=audio_url)


def mark_job_failed(job_id: str) -> bool:
    """Transition job to failed status."""
    return update_job_status(job_id, "failed")


# ================================
# AUDIO FILE STORAGE
# ================================

# Allowed audio file extensions for input files
ALLOWED_INPUT_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}

# Allowed audio formats for output (TTS)
ALLOWED_OUTPUT_FORMATS = {"wav", "mp3", "ogg", "m4a"}


def _sanitize_extension(extension: str) -> str:
    """
    Sanitize and validate file extension.
    
    Args:
        extension: File extension (with or without leading dot)
        
    Returns:
        str: Sanitized extension with leading dot
        
    Raises:
        ValueError: If extension is invalid or contains path separators
    """
    # Remove leading dot if present
    ext = extension.lstrip(".")
    
    # Check for path traversal attempts
    if "/" in ext or "\\" in ext or ".." in ext:
        raise ValueError("Invalid extension: contains path separators")
    
    # Normalize to lowercase
    ext = ext.lower()
    
    # Add leading dot
    return f".{ext}"


def _get_extension_from_filename(filename: str) -> Optional[str]:
    """
    Extract and sanitize extension from filename.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized extension with leading dot, or None if no extension
    """
    # Extract extension
    _, ext = os.path.splitext(filename)
    
    if not ext:
        return None
    
    return _sanitize_extension(ext)


def save_input_audio(file_bytes: bytes, original_filename: str) -> str:
    """
    Save uploaded input audio file.
    
    Generates a unique filename using UUID and preserves original extension.
    Saves to static/audio/ directory.
    
    Args:
        file_bytes: Raw audio file bytes
        original_filename: Original filename from upload
        
    Returns:
        str: Relative URL path (e.g., "/static/audio/<uuid>.<ext>")
        
    Raises:
        ValueError: If filename is invalid or extension is not allowed
        OSError: If file cannot be written
    """
    if not file_bytes:
        raise ValueError("File bytes cannot be empty")
    
    if not original_filename or not original_filename.strip():
        raise ValueError("Original filename cannot be empty")
    
    # Extract and sanitize extension
    ext = _get_extension_from_filename(original_filename)
    
    if ext is None:
        raise ValueError("Filename must have a valid extension")
    
    # Validate extension is allowed
    if ext not in ALLOWED_INPUT_EXTENSIONS:
        raise ValueError(
            f"Extension {ext} not allowed. Allowed: {', '.join(ALLOWED_INPUT_EXTENSIONS)}"
        )
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}{ext}"
    file_path = AUDIO_DIR / filename
    
    # Ensure directory exists (should already exist, but be safe)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if file already exists (shouldn't happen with UUID, but be safe)
    if file_path.exists():
        raise OSError(f"File already exists: {filename}")
    
    # Write file
    try:
        file_path.write_bytes(file_bytes)
    except OSError as e:
        raise OSError(f"Failed to save audio file: {str(e)}") from e
    
    # Return absolute URL from app root (e.g., "/static/audio/<filename>")
    # Must NOT include /voice prefix or be relative like "static/audio/..."
    return f"/static/audio/{filename}"


def save_output_audio(audio_bytes: bytes, format: str) -> str:
    """
    Save generated TTS audio file.
    
    Generates a unique filename using UUID with the specified format extension.
    Saves to static/audio/ directory.
    
    Args:
        audio_bytes: Generated audio bytes
        format: Audio format (e.g., "wav", "mp3")
        
    Returns:
        str: Relative URL path (e.g., "/static/audio/<uuid>.<format>")
        
    Raises:
        ValueError: If format is invalid or audio_bytes is empty
        OSError: If file cannot be written
    """
    if not audio_bytes:
        raise ValueError("Audio bytes cannot be empty")
    
    if not format or not format.strip():
        raise ValueError("Format cannot be empty")
    
    # Sanitize and validate format
    ext = _sanitize_extension(format)
    
    # Validate format is allowed
    format_lower = format.lower().lstrip(".")
    if format_lower not in ALLOWED_OUTPUT_FORMATS:
        raise ValueError(
            f"Format '{format}' not allowed. Allowed: {', '.join(ALLOWED_OUTPUT_FORMATS)}"
        )
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}{ext}"
    file_path = AUDIO_DIR / filename
    
    # Ensure directory exists (should already exist, but be safe)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if file already exists (shouldn't happen with UUID, but be safe)
    if file_path.exists():
        raise OSError(f"File already exists: {filename}")
    
    # Write file
    try:
        file_path.write_bytes(audio_bytes)
    except OSError as e:
        raise OSError(f"Failed to save audio file: {str(e)}") from e
    
    # Return absolute URL from app root (e.g., "/static/audio/<filename>")
    # Must NOT include /voice prefix or be relative like "static/audio/..."
    return f"/static/audio/{filename}"

