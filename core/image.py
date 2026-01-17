"""
Grok image generation module.

Handles image generation via Grok/xAI API.
Silently disables if API key is missing or errors occur.
"""
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

api_key = os.getenv("GROK_API_KEY_image")
if api_key:
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
    except Exception:
        client = None
        logger.warning("Failed to initialize Grok image client")
else:
    client = None


def generate_image(prompt: str) -> Optional[str]:
    """
    Generate an image using Grok API.
    
    Args:
        prompt: The image generation prompt
        
    Returns:
        image_url if successful, None otherwise
    """
    if client is None:
        return None
    
    try:
        # Note: xAI/Grok may use different endpoint for images
        # Using images/generations endpoint similar to OpenAI DALL-E
        response = client.images.generate(
            model="grok-image",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        
        if response.data and len(response.data) > 0:
            image_url = response.data[0].url
            logger.info("Image generated successfully")
            return image_url
        else:
            return None
    except Exception as e:
        # Silently handle all errors - don't expose to client
        logger.debug(f"Image generation failed: {str(e)}")
        return None

