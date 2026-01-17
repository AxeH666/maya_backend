"""
Pika video generation provider implementation.

This module handles video generation via the Pika API.
If API keys are missing, it falls back to mocked behavior.
"""
import os
import uuid
import logging
from typing import Optional
from datetime import datetime
from video.base import VideoProvider, VideoJob
from video.polling import create_job, get_job, mark_job_processing, mark_job_ready, mark_job_failed

logger = logging.getLogger(__name__)

# TODO: Set PIKA_API_KEY in environment for production
PIKA_API_KEY = os.getenv("PIKA_API_KEY")
PIKA_ENDPOINT = "https://api.pika.art/v1/video"
PIKA_STATUS_ENDPOINT = "https://api.pika.art/v1/video/status"

# Use mock mode if API key is missing
USE_MOCK = not bool(PIKA_API_KEY)

# Lazy import httpx only when needed (in non-mock mode)
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    if not USE_MOCK:
        logger.warning("httpx not available - Pika provider will use mock mode")


class PikaProvider(VideoProvider):
    """
    Pika video generation provider.
    
    If PIKA_API_KEY is not set, falls back to mocked behavior
    to allow development/testing without API keys.
    """
    
    def __init__(self):
        self.provider_name = "pika"
        if USE_MOCK:
            logger.warning("PIKA_API_KEY not set - using mock mode")
    
    async def create_video(self, prompt: str, user_id: Optional[str] = None) -> str:
        """
        Create a new video generation job.
        
        If API key is missing, simulates job creation with mock data.
        Actual Pika API integration happens when PIKA_API_KEY is set.
        
        Args:
            prompt: The video generation prompt
            user_id: Optional user identifier if authenticated
            
        Returns:
            job_id: Unique identifier for the job
            
        Raises:
            Exception: If job creation fails (only in real API mode)
        """
        # Generate job ID and create job in tracking system
        job_id = str(uuid.uuid4())
        create_job(job_id, provider=self.provider_name, user_id=user_id)
        
        if USE_MOCK:
            # Mock mode: simulate async processing
            # In real implementation, this would call Pika API
            logger.info(f"[MOCK] Created Pika job {job_id} for prompt: {prompt[:50]}...")
            mark_job_processing(job_id)
            
            # TODO: Replace with real Pika API call:
            # headers = {
            #     "Authorization": f"Bearer {PIKA_API_KEY}",
            #     "Content-Type": "application/json"
            # }
            # payload = {
            #     "prompt": prompt,
            #     "style": "cinematic",
            #     "duration": 4
            # }
            # async with httpx.AsyncClient(timeout=60) as client:
            #     res = await client.post(PIKA_ENDPOINT, json=payload, headers=headers)
            #     res.raise_for_status()
            #     data = res.json()
            #     pika_job_id = data.get("id")
            
            return job_id
        
        # Real Pika API integration
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available, using mock mode")
            mark_job_processing(job_id)
            return job_id
        
        headers = {
            "Authorization": f"Bearer {PIKA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "style": "cinematic",
            "duration": 4
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                res = await client.post(PIKA_ENDPOINT, json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
            
            pika_job_id = data.get("id")
            if not pika_job_id:
                logger.error("No job_id returned from Pika API")
                mark_job_failed(job_id)
                raise ValueError("No job_id returned from Pika API")
            
            # Update our job with Pika's job ID if different
            # For now, we'll use our own job_id for tracking
            mark_job_processing(job_id)
            logger.info(f"Created Pika job {job_id} (Pika ID: {pika_job_id})")
            
            return job_id
        except Exception as e:
            logger.error(f"Failed to start Pika video job: {str(e)}", exc_info=True)
            mark_job_failed(job_id)
            # Don't expose internal error details to client
            raise ValueError("Failed to start video generation job")
    
    async def check_status(self, job_id: str) -> VideoJob:
        """
        Check the status of a video generation job.
        
        Args:
            job_id: The job identifier
            
        Returns:
            VideoJob: The current job state
            
        Raises:
            ValueError: If job doesn't exist
        """
        # First check our internal tracking
        job = get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if USE_MOCK:
            # Mock mode: simulate completion after initial check
            if job.status == "processing":
                # Simulate successful completion
                mock_video_url = f"https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
                mark_job_ready(job_id, mock_video_url)
                job = get_job(job_id)
            return job
        
        # Real Pika API integration
        if not HTTPX_AVAILABLE:
            logger.warning("httpx not available, using mock mode")
            # Simulate completion
            if job.status == "processing":
                mock_video_url = f"https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
                mark_job_ready(job_id, mock_video_url)
                job = get_job(job_id)
            return job
        
        headers = {
            "Authorization": f"Bearer {PIKA_API_KEY}"
        }
        
        try:
            # TODO: Use actual Pika job ID if stored separately
            # For now, using our job_id - adjust based on Pika's API
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.get(
                    f"{PIKA_STATUS_ENDPOINT}/{job_id}",
                    headers=headers
                )
                res.raise_for_status()
                data = res.json()
            
            pika_status = data.get("status", "unknown")
            video_url = data.get("video_url") or data.get("output_url")
            
            # Normalize Pika status to our standard statuses
            if pika_status in ["completed", "done", "ready", "succeeded"]:
                if video_url and job.status != "ready":
                    mark_job_ready(job_id, video_url)
                status = "ready"
            elif pika_status in ["pending", "queued"]:
                status = "pending"
            elif pika_status in ["processing", "in_progress", "generating"]:
                if job.status == "pending":
                    mark_job_processing(job_id)
                status = "processing"
            else:  # failed, error, cancelled
                if job.status != "failed":
                    mark_job_failed(job_id)
                status = "failed"
            
            # Update job if status changed
            if status != job.status:
                job.status = status
                if video_url:
                    job.video_url = video_url
            
            return job
        except Exception as e:
            # Check if it's an HTTP error (httpx.HTTPStatusError)
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                logger.error(f"HTTP error checking Pika job {job_id}: {e}", exc_info=True)
                # If 404, mark as failed
                if e.response.status_code == 404:
                    mark_job_failed(job_id)
                    return get_job(job_id)
                # For other HTTP errors, return current job state
                return job
            
            # For other errors, log and return current job state
            logger.error(f"Error checking Pika job {job_id}: {str(e)}", exc_info=True)
            return job
