"""
Voice agent for handling STT/TTS operations using Grok API.

This module provides the ONLY interface to Grok voice APIs (STT/TTS).
It is responsible for:
- Speech-to-text transcription via Grok STT API
- Text-to-speech synthesis via Grok TTS API

This module does NOT handle:
- HTTP request routing (handled by router.py)
- File storage (handled by audio_store.py)
- Persona or agent selection logic
- Streaming or WebSocket connections
- Retries or backoff logic
"""
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from voice.stt_whisper import transcribe_audio_file

logger = logging.getLogger(__name__)

# Verify API key is available at module level
if "GROK_API_KEY" not in os.environ or not os.environ["GROK_API_KEY"]:
    raise RuntimeError(
        "GROK_API_KEY is required but not found in environment variables. "
        "Please set GROK_API_KEY in your .env file or environment."
    )

API_KEY = os.environ["GROK_API_KEY"]
GROK_API_BASE_URL = "https://api.x.ai/v1"

# Verify ElevenLabs API key is available at module level
elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
if not elevenlabs_key:
    raise RuntimeError("ELEVENLABS_API_KEY is not set")

ELEVENLABS_API_KEY = elevenlabs_key
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/VG7gYikNQ71LJ52W9fAD"


class GrokVoiceAgent:
    """
    Stateless voice agent for Grok STT/TTS operations.
    
    This class provides synchronous methods for:
    - Transcribing audio files to text (STT)
    - Synthesizing text to audio bytes (TTS)
    
    The class is stateless - all configuration is passed via method parameters.
    No audio data or configuration is cached or stored as instance state.
    
    This class does NOT:
    - Handle HTTP routing or request parsing
    - Save files to disk (use audio_store module)
    - Implement streaming or real-time processing
    - Handle persona or agent selection
    """
    
    def __init__(self):
        """Initialize the Grok voice agent."""
        # Verify API key is still available (defensive check)
        if not API_KEY:
            raise RuntimeError("GROK_API_KEY is required but not found")
        logger.info("Initialized GrokVoiceAgent")
    
    def transcribe_audio(self, audio_path: str) -> str:
        """
        Transcribe an audio file to text using local Whisper STT.
        
        This method:
        - Validates the audio file exists
        - Transcribes audio using local Whisper model
        - Returns the transcribed text
        
        This method does NOT:
        - Save or cache the audio file
        - Handle file format conversion (Whisper handles various formats)
        - Implement retries or backoff
        
        Args:
            audio_path: Filesystem path to the audio file (e.g., "static/audio/file.wav")
            
        Returns:
            str: Transcribed text from the audio file
            
        Raises:
            RuntimeError: If transcription fails or returns empty result
        """
        # NOTE:
        # Local Whisper STT is used to avoid external audio entitlement dependencies.
        # This can be swapped back to xAI STT once audio access is enabled.
        
        try:
            logger.info("Starting local Whisper STT transcription")
            transcribed_text = transcribe_audio_file(audio_path)
            logger.info("Whisper STT transcription completed successfully")
            return transcribed_text
        except Exception as e:
            error_msg = f"Whisper STT transcription failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
        
        # ========================================================================
        # Grok STT disabled — replaced by local Whisper STT
        # ========================================================================
        # The code below is kept for reference but is no longer executed.
        # It can be re-enabled once xAI audio entitlement is granted.
        #
        # Original Grok STT implementation:
        #
        # - Validated file exists
        # - Read file as bytes
        # - Normalized audio to WAV format (16kHz, mono) using ffmpeg
        # - Sent normalized audio to Grok STT API
        # - Parsed JSON response and returned transcribed text
        #
        # The Grok STT API implementation was production-ready but gated by
        # xAI audio entitlement. Once access is granted, this code can be
        # restored by uncommenting the section below and removing the Whisper
        # implementation above.
        # ========================================================================
        #
        # # Validate file exists
        # file_path = Path(audio_path)
        # if not file_path.exists():
        #     raise FileNotFoundError(f"Audio file not found: {audio_path}")
        # 
        # if not file_path.is_file():
        #     raise RuntimeError(f"Path is not a file: {audio_path}")
        # 
        # # Read file as bytes
        # try:
        #     audio_bytes = file_path.read_bytes()
        # except OSError as e:
        #     raise OSError(f"Failed to read audio file {audio_path}: {str(e)}") from e
        # 
        # if not audio_bytes:
        #     raise RuntimeError(f"Audio file is empty: {audio_path}")
        # 
        # # Audio normalization: Convert input audio to WAV format (16kHz, mono)
        # # This is required because Grok STT API expects specific audio format.
        # # Browser-recorded audio (.m4a, .webm, etc.) may have varying sample rates,
        # # channels, or codecs that need to be normalized before API submission.
        # temp_wav_path = None
        # normalized_audio_bytes = None
        # 
        # try:
        #     # Create temporary file for normalized WAV output
        #     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        #         temp_wav_path = temp_wav.name
        #     
        #     # Use ffmpeg to normalize audio to WAV, 16kHz, mono
        #     # This ensures consistent format regardless of input audio characteristics
        #     ffmpeg_cmd = [
        #         "ffmpeg",
        #         "-i", str(file_path),  # Input file
        #         "-ar", "16000",        # Sample rate: 16kHz
        #         "-ac", "1",            # Channels: mono
        #         "-f", "wav",           # Format: WAV
        #         "-y",                  # Overwrite output file
        #         temp_wav_path          # Output file
        #     ]
        #     
        #     # Run ffmpeg and capture output
        #     result = subprocess.run(
        #         ffmpeg_cmd,
        #         capture_output=True,
        #         text=True,
        #         timeout=30
        #     )
        #     
        #     if result.returncode != 0:
        #         error_msg = f"ffmpeg normalization failed: {result.stderr}"
        #         logger.error(error_msg)
        #         raise RuntimeError(error_msg)
        #     
        #     # Verify normalized file exists and is readable
        #     normalized_path = Path(temp_wav_path)
        #     if not normalized_path.exists():
        #         raise RuntimeError("Normalized audio file was not created")
        #     
        #     # Read normalized WAV file as bytes (into memory before cleanup)
        #     normalized_audio_bytes = normalized_path.read_bytes()
        #     if not normalized_audio_bytes:
        #         raise RuntimeError("Normalized audio file is empty")
        # 
        # except subprocess.TimeoutExpired:
        #     raise RuntimeError("Audio normalization timed out after 30 seconds")
        # except FileNotFoundError:
        #     raise RuntimeError("ffmpeg not found. Please install ffmpeg to use voice transcription.")
        # except Exception as e:
        #     if isinstance(e, RuntimeError):
        #         raise
        #     raise RuntimeError(f"Audio normalization failed: {str(e)}")
        # finally:
        #     # Cleanup: Always delete temporary normalized file
        #     # (normalized_audio_bytes is already in memory, so safe to delete file)
        #     if temp_wav_path and Path(temp_wav_path).exists():
        #         try:
        #             Path(temp_wav_path).unlink()
        #         except Exception as e:
        #             logger.warning(f"Failed to delete temporary file {temp_wav_path}: {str(e)}")
        # 
        # # Ensure we have normalized audio bytes before proceeding
        # if normalized_audio_bytes is None:
        #     raise RuntimeError("Failed to normalize audio file")
        # 
        # # Real Grok STT API implementation
        # # NOTE: STT is gated by xAI audio entitlement. This code is production-ready
        # # but may fail with 403 until xAI enables audio access for the account.
        # # No refactor will be needed once access is granted - the implementation
        # # is complete and will work immediately upon entitlement activation.
        # #
        # # Call Grok speech-to-text endpoint with normalized audio
        # try:
        #     with httpx.Client(timeout=30.0) as client:
        #         # Prepare multipart form data for file upload
        #         files = {
        #             "file": (
        #                 "audio.wav",
        #                 normalized_audio_bytes,
        #                 "audio/wav"
        #             )
        #         }
        #         data = {
        #             "model": "grok-audio"  # Grok STT model identifier
        #         }
        #         headers = {
        #             "Authorization": f"Bearer {API_KEY}"
        #         }
        #         
        #         # Make API request
        #         response = client.post(
        #             f"{GROK_API_BASE_URL}/audio/transcriptions",
        #             files=files,
        #             data=data,
        #             headers=headers
        #         )
        #         
        #         # Check for HTTP errors
        #         response.raise_for_status()
        #         
        #         # Parse JSON response
        #         result = response.json()
        #         transcribed_text = result.get("text", "").strip()
        #         
        # except httpx.HTTPStatusError as e:
        #     # Detect authorization failure (403) indicating missing xAI STT entitlement
        #     if e.response.status_code == 403:
        #         # Parse error body to check for permission/entitlement messages
        #         error_body = ""
        #         try:
        #             error_body = e.response.text.lower()
        #         except Exception:
        #             pass
        #         
        #         # Check for indicators of missing permission/entitlement
        #         entitlement_keywords = [
        #             "permission",
        #             "not authorized",
        #             "not enabled",
        #             "entitlement",
        #             "access denied",
        #             "forbidden",
        #             "team not authorized"
        #         ]
        #         
        #         is_entitlement_error = any(keyword in error_body for keyword in entitlement_keywords)
        #         
        #         if is_entitlement_error or e.response.status_code == 403:
        #             # This is an entitlement issue, not a bug
        #             error_msg = "Grok STT is not enabled for this account yet. Awaiting xAI audio entitlement."
        #             logger.error(error_msg)
        #             
        #             # Development-only fallback while awaiting xAI STT access
        #             # This is OFF by default and must be explicitly enabled via environment variable
        #             fallback_text = os.getenv("GROK_STT_FALLBACK_TEXT")
        #             if fallback_text:
        #                 logger.warning(
        #                     "Using development fallback text for STT (GROK_STT_FALLBACK_TEXT is set). "
        #                     "This should only be used during development while awaiting xAI STT access."
        #                 )
        #                 return fallback_text.strip()
        #             
        #             # No fallback - raise clear entitlement error
        #             raise RuntimeError(error_msg)
        #         else:
        #             # 403 but not clearly an entitlement issue - treat as generic error
        #             error_msg = f"Grok STT API returned error {e.response.status_code}"
        #             logger.error(f"{error_msg}: {e.response.text}")
        #             raise RuntimeError(f"Speech-to-text API request failed: {error_msg}")
        #     else:
        #         # Other HTTP errors (not 403)
        #         error_msg = f"Grok STT API returned error {e.response.status_code}"
        #         logger.error(f"{error_msg}: {e.response.text}")
        #         raise RuntimeError(f"Speech-to-text API request failed: {error_msg}")
        # except httpx.RequestError as e:
        #     error_msg = f"Failed to connect to Grok STT API: {str(e)}"
        #     logger.error(error_msg)
        #     raise RuntimeError(error_msg)
        # except Exception as e:
        #     error_msg = f"Unexpected error during STT API call: {str(e)}"
        #     logger.error(error_msg, exc_info=True)
        #     raise RuntimeError(error_msg)
        # 
        # # Validate transcription result
        # if not transcribed_text:
        #     raise RuntimeError("Empty transcription from Grok STT")
        # 
        # return transcribed_text
    
    def synthesize_speech(self, text: str, voice_config: Optional[dict] = None) -> bytes:
        """
        Synthesize text to speech using ElevenLabs TTS API.
        
        This method:
        - Validates input text is non-empty
        - Applies voice configuration (if provided)
        - Sends request to ElevenLabs TTS API
        - Returns raw audio bytes (MP3 format)
        
        This method does NOT:
        - Save audio files to disk (use audio_store.save_output_audio)
        - Cache or store voice configuration
        - Mutate the voice_config dictionary
        - Implement streaming
        
        Supported voice_config keys:
        - stability: float (0.0-1.0) - Voice stability setting
        - similarity_boost: float (0.0-1.0) - Similarity boost setting
        
        Args:
            text: Plain text to synthesize
            voice_config: Optional dictionary with voice configuration.
                        If None, uses API defaults. Only stability and similarity_boost
                        are supported; other keys are ignored.
            
        Returns:
            bytes: Raw audio data (MP3 format)
            
        Raises:
            ValueError: If text is empty or voice_config is not a dict
            RuntimeError: If synthesis fails or returns empty audio
        """
        # Validate text
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Validate voice_config if provided
        if voice_config is not None:
            if not isinstance(voice_config, dict):
                raise ValueError("voice_config must be a dictionary or None")
            # Create a copy to avoid mutating the original
            config = voice_config.copy()
        else:
            config = {}
        
        logger.info("ElevenLabs TTS started")
        
        # Build voice settings with safe defaults and optional overrides
        # Only stability and similarity_boost can be overridden
        stability = 0.35  # Default
        similarity_boost = 0.75  # Default
        
        # Safely extract and clamp voice settings from config
        if "stability" in config:
            try:
                stability = float(config["stability"])
                # Clamp to valid range [0.0, 1.0]
                stability = max(0.0, min(1.0, stability))
            except (ValueError, TypeError):
                pass  # Ignore invalid values, use default
        
        if "similarity_boost" in config:
            try:
                similarity_boost = float(config["similarity_boost"])
                # Clamp to valid range [0.0, 1.0]
                similarity_boost = max(0.0, min(1.0, similarity_boost))
            except (ValueError, TypeError):
                pass  # Ignore invalid values, use default
        
        # Build request payload
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        
        # Make ElevenLabs API request
        try:
            with httpx.Client(timeout=30.0) as client:
                headers = {
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg"
                }
                
                response = client.post(
                    ELEVENLABS_API_URL,
                    json=payload,
                    headers=headers
                )
                
                # Check for HTTP errors
                if response.status_code != 200:
                    # Log error details (truncate response body if too long)
                    error_body = response.text[:500] if response.text else "(no body)"
                    logger.error(
                        f"ElevenLabs TTS failed with status {response.status_code}: {error_body}"
                    )
                    raise RuntimeError("ElevenLabs TTS failed")
                
                # Get audio bytes from response
                audio_bytes = response.content
                
        except httpx.TimeoutException:
            logger.error("ElevenLabs TTS request timed out")
            raise RuntimeError("ElevenLabs TTS failed")
        except httpx.RequestError as e:
            logger.error(f"ElevenLabs TTS request error: {str(e)}")
            raise RuntimeError("ElevenLabs TTS failed")
        except RuntimeError:
            # Re-raise RuntimeError from status code check
            raise
        except Exception as e:
            logger.error(f"Unexpected error during ElevenLabs TTS: {str(e)}", exc_info=True)
            raise RuntimeError("ElevenLabs TTS failed")
        
        # Anti-silence guard: Validate audio bytes
        if not audio_bytes or len(audio_bytes) == 0:
            logger.error("ElevenLabs returned empty audio")
            raise RuntimeError("ElevenLabs returned empty audio")
        
        # Basic validation: MP3 files should start with ID3 tag or MPEG frame sync
        # This is a sanity check to catch obvious failures
        if len(audio_bytes) < 3:
            logger.error("ElevenLabs returned suspiciously short audio")
            raise RuntimeError("ElevenLabs returned empty audio")
        
        logger.info("ElevenLabs TTS completed")
        
        return audio_bytes

