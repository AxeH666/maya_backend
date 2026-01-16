from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class VideoJob:
    """
    Standardized video job contract.
    All providers must return jobs matching this structure.
    """
    job_id: str
    status: str  # "pending" | "processing" | "ready" | "failed"
    video_url: Optional[str]
    provider: str
    created_at: datetime

    def to_dict(self) -> dict:
        """Convert VideoJob to dictionary for API responses."""
        return {
            "status": self.status,
            "video_url": self.video_url
        }


class VideoProvider(ABC):
    """
    Abstract interface for video generation providers.
    All providers must implement create_video and check_status.
    """
    
    @abstractmethod
    async def create_video(self, prompt: str) -> str:
        """
        Create a new video generation job.
        
        Args:
            prompt: The video generation prompt
            
        Returns:
            job_id: Unique identifier for the job
            
        Raises:
            Exception: If job creation fails
        """
        pass

    @abstractmethod
    async def check_status(self, job_id: str) -> VideoJob:
        """
        Check the status of a video generation job.
        
        Args:
            job_id: The job identifier
            
        Returns:
            VideoJob: The current job state
            
        Raises:
            Exception: If job lookup fails or job doesn't exist
        """
        pass
