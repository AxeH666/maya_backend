"""
FastAPI application for Maya backend.

Handles chat interactions with optional video generation.
Uses video provider system for async video job management.
"""
import logging
import os
import asyncio
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.llm import generate_reply
from video.factory import get_video_provider
from video.polling import get_job as get_video_job
from image.factory import get_image_provider
from image.polling import get_job as get_image_job
from auth.router import router as auth_router
from auth.deps import get_current_user_optional
from auth.models import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router)

# Mount static files for serving generated images
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
(static_dir / "images").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize providers
video_provider = get_video_provider()
image_provider = get_image_provider()


class ChatRequest(BaseModel):
    message: str
    image_generation: bool = False
    video_generation: bool = False


@app.post("/chat")
async def chat(
    req: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Handle chat requests with optional image and video generation.
    
    Returns text response and optionally image_job_id or video_job_id.
    Both image and video generation happen asynchronously - job status can be checked
    via GET /image/{job_id} or GET /video/{job_id}.
    
    Response format:
    {
        "text": string,
        "video_job_id": string | null,
        "image_job_id": string | null
    }
    """
    # Generate text reply from LLM
    reply_data = generate_reply(req.message)
    text = reply_data["text"]
    
    # Start image generation asynchronously if requested
    image_job_id = None
    if req.image_generation:
        try:
            # Combine user message with system personality prompt for image generation
            from prompts.system import MAYA_SYSTEM_PROMPT
            image_prompt = f"{MAYA_SYSTEM_PROMPT.strip()}\n\nCreate an image: {req.message}"
            
            # Create image job asynchronously
            # This starts the job but doesn't block waiting for completion
            user_id = str(current_user.id) if current_user else None
            image_job_id = await image_provider.create_image(image_prompt, user_id=user_id)
            logger.info(f"Created image job {image_job_id} for message")
        except Exception as e:
            # Full error logging
            error_msg = f"Failed to create image job: {str(e)}"
            print(f"IMAGE GENERATION ERROR: {error_msg}")
            logger.error(f"IMAGE GENERATION ERROR: {error_msg}", exc_info=True)
            # Don't expose stack traces to client, but log fully
    
    # Start video generation asynchronously if requested
    video_job_id = None
    if req.video_generation:
        try:
            # Create video job asynchronously
            # This starts the job but doesn't block waiting for completion
            user_id = str(current_user.id) if current_user else None
            video_job_id = await video_provider.create_video(req.message, user_id=user_id)
            logger.info(f"Created video job {video_job_id} for message")
        except Exception as e:
            # Log error but don't crash - just return without video_job_id
            logger.error(f"Failed to create video job: {str(e)}", exc_info=True)
            # Don't expose stack traces to client
    
    return {
        "text": text,
        "video_job_id": video_job_id,
        "image_job_id": image_job_id
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
        job = get_video_job(job_id)
        if job:
            return job.to_dict()
        
        # Job doesn't exist
        logger.warning(f"Video job {job_id} not found")
        return {"status": "not_found"}
    except Exception as e:
        # Log error but return safe response
        logger.error(f"Error checking video job {job_id}: {str(e)}", exc_info=True)
        
        # Try to get job from polling store as fallback
        job = get_video_job(job_id)
        if job:
            return job.to_dict()
        
        return {"status": "failed", "video_url": None}


@app.get("/image/{job_id}")
async def get_image(job_id: str):
    """
    Get the status of an image generation job.
    
    Returns:
    {
        "status": "pending" | "processing" | "ready" | "failed",
        "image_url": string | null
    }
    
    Or:
    {
        "status": "not_found"
    }
    """
    try:
        # Check job status via provider
        job = await image_provider.check_status(job_id)
        
        # Convert ImageJob to API response format
        return job.to_dict()
    except ValueError:
        # Job not found in provider's tracking
        # Also check polling store as fallback
        job = get_image_job(job_id)
        if job:
            return job.to_dict()
        
        # Job doesn't exist
        logger.warning(f"Image job {job_id} not found")
        return {"status": "not_found"}
    except Exception as e:
        # Log error but return safe response
        logger.error(f"Error checking image job {job_id}: {str(e)}", exc_info=True)
        
        # Try to get job from polling store as fallback
        job = get_image_job(job_id)
        if job:
            return job.to_dict()
        
        return {"status": "failed", "image_url": None}


class ImageGenerateRequest(BaseModel):
    """Request model for ComfyUI image generation endpoint."""
    prompt: str
    negative_prompt: str = ""
    width: int = 512
    height: int = 768
    steps: int = 30
    cfg: float = 8.0
    seed: int = 0


@app.post("/maya/image")
async def generate_image(
    req: ImageGenerateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generate an image using ComfyUI wrapper API.
    
    This endpoint accepts the full ComfyUI API contract and creates
    an image generation job asynchronously.
    
    Request format:
    {
        "prompt": "string (required)",
        "negative_prompt": "string (optional, default: empty)",
        "width": "int (default: 512, must be multiple of 8)",
        "height": "int (default: 768, must be multiple of 8)",
        "steps": "int (default: 30)",
        "cfg": "float (default: 8.0)",
        "seed": "int (default: 0, 0 = random)"
    }
    
    Response format:
    {
        "job_id": "string (UUID)",
        "status": "pending"
    }
    """
    # Validate inputs
    if not req.prompt or not req.prompt.strip():
        return {"error": "Prompt cannot be empty", "status": "error"}
    
    if req.width % 8 != 0 or req.height % 8 != 0:
        return {"error": "Width and height must be multiples of 8", "status": "error"}
    
    if req.steps < 1 or req.steps > 100:
        return {"error": "Steps must be between 1 and 100", "status": "error"}
    
    if req.cfg <= 0 or req.cfg > 30:
        return {"error": "CFG scale must be between 0 and 30", "status": "error"}
    
    try:
        # Use the image provider (only accepts prompt currently)
        # Other parameters (width, height, steps, cfg, seed) are ignored
        # but validation was already done above
        user_id = str(current_user.id) if current_user else None
        job_id = await image_provider.create_image(req.prompt, user_id=user_id)
        
        logger.info(f"Created image job {job_id} via /maya/image endpoint")
        
        return {
            "job_id": job_id,
            "status": "pending"
        }
    except Exception as e:
        error_msg = f"Failed to create image job: {str(e)}"
        logger.error(f"IMAGE GENERATION ERROR: {error_msg}", exc_info=True)
        return {"error": error_msg, "status": "error"}


