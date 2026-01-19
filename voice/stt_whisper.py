"""
Local Whisper-based Speech-to-Text (STT) module.

This module provides a simple interface for transcribing audio files using
OpenAI's Whisper model running locally. The model is loaded once at module
import time and reused for all transcription requests.

This module does NOT handle:
- HTTP routing or request parsing
- File storage or management
- Streaming or real-time processing
- Language detection (forces English)
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Module-level Whisper model (loaded once at import time)
_whisper_model = None


def _load_whisper_model():
    """
    Load Whisper model once at module import time.
    
    Raises:
        RuntimeError: If Whisper package is not available or model loading fails
    """
    global _whisper_model
    
    if _whisper_model is not None:
        return
    
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "Whisper package not found. Please install whisper: pip install openai-whisper"
        )
    
    try:
        logger.info("Loading Whisper STT model (base)...")
        _whisper_model = whisper.load_model("base")
        logger.info("Whisper STT model loaded (base)")
    except Exception as e:
        error_msg = f"Failed to load Whisper model: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


# Load model immediately at import time
_load_whisper_model()


def transcribe_audio_file(audio_path: str) -> str:
    """
    Transcribe an audio file to text using local Whisper model.
    
    This function:
    - Validates the audio file exists and is readable
    - Transcribes audio to English text using Whisper
    - Returns cleaned transcription text
    
    This function does NOT:
    - Handle file format conversion (assumes Whisper can handle the format)
    - Cache transcription results
    - Perform language detection (forces English)
    
    Args:
        audio_path: Filesystem path to the audio file
        
    Returns:
        str: Transcribed text from the audio file (non-empty, stripped)
        
    Raises:
        RuntimeError: If audio file is not found, transcription fails, or result is empty
    """
    # Validate input
    file_path = Path(audio_path)
    if not file_path.exists():
        raise RuntimeError(f"Audio file not found: {audio_path}")
    
    if not file_path.is_file():
        raise RuntimeError(f"Path is not a file: {audio_path}")
    
    # Ensure model is loaded (defensive check)
    if _whisper_model is None:
        raise RuntimeError("Whisper model not loaded")
    
    # Perform transcription
    try:
        logger.info("Starting local Whisper STT transcription")
        
        # Transcribe with Whisper (force English, no auto language detection)
        result = _whisper_model.transcribe(
            str(file_path),
            language="en",
            task="transcribe"
        )
        
        # Extract text from result
        transcribed_text = result.get("text", "").strip()
        
        # Validate transcription result
        if not transcribed_text:
            raise RuntimeError("Empty transcription result")
        
        logger.info("Whisper STT transcription completed successfully")
        return transcribed_text
        
    except Exception as e:
        error_msg = f"Whisper transcription failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e

