"""
Video provider factory.

Centralizes provider creation and makes it easy to add new providers
(like Runway, WAN) without modifying main.py.
"""
import os
import logging
from video.pika import PikaProvider
from video.mock import MockProvider

logger = logging.getLogger(__name__)

# Default provider is Pika
VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "pika")


def get_video_provider():
    """
    Get video provider based on VIDEO_PROVIDER env var.
    
    Defaults to 'pika' if not set. PikaProvider will use mock mode
    if PIKA_API_KEY is missing, so it's safe to use in development.
    
    Returns:
        VideoProvider: The configured video provider instance
    """
    provider_name = VIDEO_PROVIDER.lower()
    
    if provider_name == "pika":
        # PikaProvider handles mock mode internally if API key is missing
        return PikaProvider()
    elif provider_name == "mock":
        # Explicit mock provider for testing
        return MockProvider()
    # TODO: Add Runway provider
    # elif provider_name == "runway":
    #     return RunwayProvider()
    # TODO: Add WAN provider
    # elif provider_name == "wan":
    #     return WANProvider()
    else:
        logger.warning(f"Unknown provider '{provider_name}', defaulting to Pika")
        return PikaProvider()
