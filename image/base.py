from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ImageJob:
    """
    Standardized image job contract.
    All providers must return jobs matching this structure.
    """
    job_id: str
    status: str  # "pending" | "processing" | "ready" | "failed"
    image_url: Optional[str]
    provider: str
    created_at: datetime
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert ImageJob to dictionary for API responses."""
        return {
            "status": self.status,
            "image_url": self.image_url
        }


class ImageProvider(ABC):
    """
    Abstract interface for image generation providers.
    All providers must implement create_image and check_status.
    """
    
    @abstractmethod
    async def create_image(self, prompt: str, user_id: Optional[str] = None) -> str:
        """
        Create a new image generation job.
        
        Args:
            prompt: The image generation prompt
            user_id: Optional user identifier if authenticated
            
        Returns:
            job_id: Unique identifier for the job
            
        Raises:
            Exception: If job creation fails
        """
        pass

    @abstractmethod
    async def check_status(self, job_id: str) -> ImageJob:
        """
        Check the status of an image generation job.
        
        Args:
            job_id: The job identifier
            
        Returns:
            ImageJob: The current job state
            
        Raises:
            Exception: If job lookup fails or job doesn't exist
        """
        pass


