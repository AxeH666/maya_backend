"""
Centralized video job tracking and state management.

This module maintains an in-memory store of all video jobs,
handling state transitions and providing a single source of truth.
"""
from typing import Dict, Optional
from datetime import datetime
from video.base import VideoJob

# In-memory job store
# TODO: Replace with database in production
_JOBS: Dict[str, VideoJob] = {}


def create_job(job_id: str, provider: str, user_id: Optional[str] = None) -> VideoJob:
    """
    Create a new job with pending status.
    
    Args:
        job_id: Unique job identifier
        provider: Provider name (e.g., "pika", "runway")
        user_id: Optional user identifier if authenticated
        
    Returns:
        VideoJob: The newly created job
    """
    job = VideoJob(
        job_id=job_id,
        status="pending",
        video_url=None,
        provider=provider,
        created_at=datetime.now(),
        user_id=user_id
    )
    _JOBS[job_id] = job
    return job


def get_job(job_id: str) -> Optional[VideoJob]:
    """
    Retrieve a job by ID.
    
    Args:
        job_id: The job identifier
        
    Returns:
        VideoJob if found, None otherwise
    """
    return _JOBS.get(job_id)


def update_job_status(job_id: str, status: str, video_url: Optional[str] = None) -> bool:
    """
    Update job status and optionally video_url.
    Handles state transitions: pending → processing → ready/failed
    
    Args:
        job_id: The job identifier
        status: New status ("pending" | "processing" | "ready" | "failed")
        video_url: Optional video URL when status is "ready"
        
    Returns:
        True if update succeeded, False if job not found
    """
    if job_id not in _JOBS:
        return False
    
    job = _JOBS[job_id]
    job.status = status
    if video_url is not None:
        job.video_url = video_url
    
    return True


def mark_job_processing(job_id: str) -> bool:
    """Transition job from pending to processing."""
    return update_job_status(job_id, "processing")


def mark_job_ready(job_id: str, video_url: str) -> bool:
    """Transition job to ready status with video URL."""
    return update_job_status(job_id, "ready", video_url)


def mark_job_failed(job_id: str) -> bool:
    """Transition job to failed status."""
    return update_job_status(job_id, "failed")
