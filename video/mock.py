"""
Mock video provider for testing and fallback scenarios.

Simulates async video generation with immediate completion.
Used for development and testing when real API keys aren't available.
"""
import uuid
from datetime import datetime
from video.base import VideoProvider, VideoJob
from video.polling import create_job, get_job, mark_job_processing, mark_job_ready


class MockProvider(VideoProvider):
    """
    Mock video provider for testing and fallback scenarios.
    
    Simulates async video generation with immediate completion
    after first status check. Used when real providers aren't available.
    """
    
    def __init__(self):
        self.provider_name = "mock"
    
    async def create_video(self, prompt: str) -> str:
        """
        Create a mock video job.
        
        Args:
            prompt: The video generation prompt (ignored in mock mode)
            
        Returns:
            job_id: Unique identifier for the job
        """
        job_id = str(uuid.uuid4())
        create_job(job_id, provider=self.provider_name)
        mark_job_processing(job_id)
        return job_id
    
    async def check_status(self, job_id: str) -> VideoJob:
        """
        Check status of a mock video job.
        
        Simulates completion after first check - transitions
        processing → ready with a mock video URL.
        
        Args:
            job_id: The job identifier
            
        Returns:
            VideoJob: The current job state
            
        Raises:
            ValueError: If job doesn't exist
        """
        job = get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Simulate completion after first check
        if job.status == "processing":
            mock_video_url = f"https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
            mark_job_ready(job_id, mock_video_url)
            job = get_job(job_id)
        
        return job


