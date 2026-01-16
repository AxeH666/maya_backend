"""
FastAPI application for Maya backend.

Handles chat interactions with optional video generation.
Uses video provider system for async video job management.
"""
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from core.llm import generate_reply
from video.factory import get_video_provider
from video.polling import get_job

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize video provider (defaults to Pika)
video_provider = get_video_provider()


class ChatRequest(BaseModel):
    message: str
    want_video: bool = False


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Handle chat requests with optional video generation.
    
    Returns text response and optionally a video_job_id if want_video=true.
    Video generation happens asynchronously - job status can be checked
    via GET /video/{job_id}.
    
    Response format:
    {
        "text": string,
        "video_job_id": string | null
    }
    """
    # Generate text reply from LLM
    reply_data = generate_reply(req.message)
    text = reply_data["text"]
    
    # Start video generation asynchronously if requested
    video_job_id = None
    if req.want_video:
        try:
            # Create video job asynchronously
            # This starts the job but doesn't block waiting for completion
            video_job_id = await video_provider.create_video(req.message)
            logger.info(f"Created video job {video_job_id} for message")
        except Exception as e:
            # Log error but don't crash - just return without video_job_id
            logger.error(f"Failed to create video job: {str(e)}", exc_info=True)
            # Don't expose stack traces to client
    
    return {
        "text": text,
        "video_job_id": video_job_id
    }


@app.get("/video/{job_id}")
async def get_video(job_id: str):
    """
    Get the status of a video generation job.
    
    Returns:
    {
        "status": "pending" | "processing" | "ready" | "failed",
        "video_url": string | null
    }
    
    Or:
    {
        "status": "not_found"
    }
    """
    try:
        # Check job status via provider
        job = await video_provider.check_status(job_id)
        
        # Convert VideoJob to API response format
        return job.to_dict()
    except ValueError:
        # Job not found in provider's tracking
        # Also check polling store as fallback
        job = get_job(job_id)
        if job:
            return job.to_dict()
        
        # Job doesn't exist
        logger.warning(f"Video job {job_id} not found")
        return {"status": "not_found"}
    except Exception as e:
        # Log error but return safe response
        logger.error(f"Error checking video job {job_id}: {str(e)}", exc_info=True)
        
        # Try to get job from polling store as fallback
        job = get_job(job_id)
        if job:
            return job.to_dict()
        
        return {"status": "failed", "video_url": None}
