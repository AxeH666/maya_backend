"""
Centralized image job tracking and state management.

This module maintains an in-memory store of all image jobs,
handling state transitions and providing a single source of truth.
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from image.base import ImageJob

logger = logging.getLogger(__name__)

# In-memory job store
# TODO: Replace with database in production
_JOBS: Dict[str, ImageJob] = {}


def create_job(job_id: str, provider: str, user_id: Optional[str] = None) -> ImageJob:
    """
    Create a new job with pending status.
    
    Args:
        job_id: Unique job identifier
        provider: Provider name (e.g., "grok", "openai")
        user_id: Optional user identifier if authenticated
        
    Returns:
        ImageJob: The newly created job
    """
    job = ImageJob(
        job_id=job_id,
        status="pending",
        image_url=None,
        provider=provider,
        created_at=datetime.now(),
        user_id=user_id
    )
    _JOBS[job_id] = job
    return job


def get_job(job_id: str) -> Optional[ImageJob]:
    """
    Retrieve a job by ID.
    
    Args:
        job_id: The job identifier
        
    Returns:
        ImageJob if found, None otherwise
    """
    job = _JOBS.get(job_id)
    
    # If job exists and is marked ready, verify file exists
    if job and job.status == "ready" and job.image_url:
        from pathlib import Path
        # Extract filename from image_url (e.g., "/static/images/maya_123.png" -> "maya_123.png")
        image_filename = Path(job.image_url).name
        static_dir = Path(__file__).parent.parent / "static" / "images"
        image_path = static_dir / image_filename
        
        if not image_path.exists():
            # File missing, mark as processing
            job.status = "processing"
            logger.warning(f"Image file missing for job {job_id}: {image_path}")
    
    return job


def update_job_status(job_id: str, status: str, image_url: Optional[str] = None) -> bool:
    """
    Update job status and optionally image_url.
    Handles state transitions: pending → processing → ready/failed
    
    Args:
        job_id: The job identifier
        status: New status ("pending" | "processing" | "ready" | "failed")
        image_url: Optional image URL when status is "ready"
        
    Returns:
        True if update succeeded, False if job not found
    """
    if job_id not in _JOBS:
        return False
    
    job = _JOBS[job_id]
    job.status = status
    if image_url is not None:
        job.image_url = image_url
    
    return True


def mark_job_processing(job_id: str) -> bool:
    """Transition job from pending to processing."""
    return update_job_status(job_id, "processing")


def mark_job_ready(job_id: str, image_url: str) -> bool:
    """Transition job to ready status with image URL."""
    return update_job_status(job_id, "ready", image_url)


def mark_job_failed(job_id: str) -> bool:
    """Transition job to failed status."""
    return update_job_status(job_id, "failed")

