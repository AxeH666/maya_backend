"""
Grok image generation provider implementation.

This module handles image generation via the Grok/xAI API.
If API keys are missing, it falls back to mocked behavior.
"""
import os
import uuid
import logging
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from image.base import ImageProvider, ImageJob
from image.polling import create_job, get_job, mark_job_processing, mark_job_ready, mark_job_failed

logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        # Fallback to current directory
        env_path = Path(".env").resolve()
    load_dotenv(env_path, override=True)
except Exception:
    # Fallback: try loading from current directory
    load_dotenv(override=True)

# TODO: Set GROK_API_KEY_IMAGE in environment for production
# Check both uppercase and lowercase variants for compatibility
GROK_API_KEY = os.getenv("GROK_API_KEY_IMAGE") or os.getenv("GROK_API_KEY_image")
USE_MOCK = not bool(GROK_API_KEY)

# Check for httpx availability (for direct HTTP requests)
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    if not USE_MOCK:
        logger.warning("httpx not available - Image provider will use mock mode")


class GrokImageProvider(ImageProvider):
    """
    Grok image generation provider.
    
    If GROK_API_KEY_image is not set, falls back to mocked behavior
    to allow development/testing without API keys.
    """
    
    def __init__(self):
        self.provider_name = "grok"
        if USE_MOCK:
            logger.warning("GROK_API_KEY_IMAGE not set - image generation disabled")
    
    async def create_image(self, prompt: str, user_id: Optional[str] = None) -> str:
        """
        Create a new image generation job.
        
        This creates the job and starts async processing in the background.
        Does not block waiting for completion.
        
        Args:
            prompt: The image generation prompt (combined from user message + system prompt)
            user_id: Optional user identifier if authenticated
            
        Returns:
            job_id: Unique identifier for the job
            
        Raises:
            Exception: If job creation fails
        """
        # Generate job ID and create job in tracking system
        job_id = str(uuid.uuid4())
        create_job(job_id, provider=self.provider_name, user_id=user_id)
        
        if USE_MOCK or not HTTPX_AVAILABLE:
            # If no API key, fail gracefully
            error_msg = "No image generation API key configured - set GROK_API_KEY_IMAGE"
            print(f"IMAGE GENERATION ERROR: {error_msg}")
            logger.error(f"IMAGE GENERATION ERROR: {error_msg}")
            mark_job_failed(job_id)
            raise ValueError(error_msg)
        
        # Mark as processing and start async generation
        mark_job_processing(job_id)
        
        # Start async image generation in background
        import asyncio
        asyncio.create_task(self._generate_image_async(job_id, prompt))
        
        logger.info(f"Started image generation job {job_id} for prompt: {prompt[:50]}...")
        return job_id
    
    async def _generate_image_async(self, job_id: str, prompt: str):
        """
        Internal async method to generate image in background.
        
        This runs as a background task and updates job status.
        
        Args:
            job_id: The job identifier
            prompt: The image generation prompt
        """
        try:
            # Use direct HTTP request to Grok/xAI API
            import httpx
            import asyncio
            
            url = "https://api.x.ai/v1/images/generations"
            
            headers = {
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "grok-2-image",
                "prompt": prompt
            }
            
            print(f"IMAGE GENERATION: Starting job {job_id}")
            print(f"IMAGE GENERATION: Prompt: {prompt[:100]}...")
            print(f"IMAGE GENERATION: Endpoint: {url}")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                print(f"IMAGE GENERATION: Status code: {response.status_code}")
                print(f"IMAGE GENERATION: Response: {response.text[:500]}")
                
                if response.status_code != 200:
                    error_msg = f"API returned status {response.status_code}: {response.text}"
                    print(f"IMAGE GENERATION ERROR: {error_msg}")
                    logger.error(f"IMAGE GENERATION ERROR for job {job_id}: {error_msg}")
                    mark_job_failed(job_id)
                    return
                
                # Parse response
                data = response.json()
                print(f"IMAGE GENERATION: Parsed response: {str(data)[:200]}")
                
                # Correct response parsing: data["data"][0]["url"]
                if "data" in data and len(data["data"]) > 0:
                    if "url" in data["data"][0]:
                        image_url = data["data"][0]["url"]
                        mark_job_ready(job_id, image_url)
                        print(f"IMAGE GENERATION: Success for job {job_id}, URL: {image_url}")
                        logger.info(f"Image generated successfully for job {job_id}")
                    else:
                        error_msg = "Response missing 'url' field in data[0]"
                        print(f"IMAGE GENERATION ERROR: {error_msg}")
                        print(f"IMAGE GENERATION ERROR: Full response: {data}")
                        logger.error(f"IMAGE GENERATION ERROR for job {job_id}: {error_msg}")
                        mark_job_failed(job_id)
                else:
                    error_msg = "Response missing 'data' array or empty"
                    print(f"IMAGE GENERATION ERROR: {error_msg}")
                    print(f"IMAGE GENERATION ERROR: Full response: {data}")
                    logger.error(f"IMAGE GENERATION ERROR for job {job_id}: {error_msg}")
                    mark_job_failed(job_id)
                    
        except httpx.HTTPError as e:
            error_msg = f"HTTP error: {str(e)}"
            print(f"IMAGE GENERATION ERROR: {error_msg}")
            logger.error(f"IMAGE GENERATION ERROR for job {job_id}: {error_msg}", exc_info=True)
            mark_job_failed(job_id)
        except KeyError as e:
            error_msg = f"Response parsing error - missing key: {str(e)}"
            print(f"IMAGE GENERATION ERROR: {error_msg}")
            logger.error(f"IMAGE GENERATION ERROR for job {job_id}: {error_msg}", exc_info=True)
            mark_job_failed(job_id)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"IMAGE GENERATION ERROR: {error_msg}")
            logger.error(f"IMAGE GENERATION ERROR for job {job_id}: {error_msg}", exc_info=True)
            mark_job_failed(job_id)
    
    async def check_status(self, job_id: str) -> ImageJob:
        """
        Check the status of an image generation job.
        
        Args:
            job_id: The job identifier
            
        Returns:
            ImageJob: The current job state
            
        Raises:
            ValueError: If job doesn't exist
        """
        # First check our internal tracking
        job = get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Image generation is synchronous with OpenAI DALL-E, so if processing
        # it should already be ready. Return current state.
        return job

