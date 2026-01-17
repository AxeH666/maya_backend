"""
Image provider factory.

Centralizes provider creation and makes it easy to add new providers
without modifying main.py.
"""
import os
import logging
from image.sd_local import SDLocalImageProvider

logger = logging.getLogger(__name__)

# Default provider is Stable Diffusion Local (ComfyUI)
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "sd_local")


def get_image_provider():
    """
    Get image provider based on IMAGE_PROVIDER env var.
    
    Defaults to 'sd_local' (ComfyUI wrapper) if not set.
    
    Returns:
        ImageProvider: The configured image provider instance
    """
    provider_name = IMAGE_PROVIDER.lower()
    
    if provider_name == "sd_local":
        # Use ComfyUI wrapper provider
        return SDLocalImageProvider()
    else:
        logger.warning(f"Unknown provider '{provider_name}', defaulting to sd_local")
        return SDLocalImageProvider()

