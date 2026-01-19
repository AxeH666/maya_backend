from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from auth.models import get_db, User
from auth.deps import get_current_user_optional
from voice.schemas import VoiceRequest, VoiceResponse, VoiceJobStatus, VoiceChatResponse
from voice.agent import GrokVoiceAgent
from voice.audio_store import save_input_audio, save_output_audio
from core.llm import generate_reply
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/chat", response_model=VoiceChatResponse)
def voice_chat(
    audio_file: UploadFile = File(...),
    chat_id: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Synchronous voice chat endpoint.
    
    Processes a complete voice chat interaction:
    1. Receives uploaded audio file
    2. Saves input audio to storage
    3. Transcribes audio to text (STT)
    4. Generates LLM reply from transcribed text
    5. Synthesizes LLM reply to speech (TTS)
    6. Saves output audio to storage
    7. Returns text reply and audio URL
    
    This endpoint is synchronous - it processes the entire flow
    before returning a response. It does NOT support:
    - Streaming responses
    - Real-time audio processing
    - WebSocket connections
    - Agent switching (uses default agent only)
    
    Args:
        audio_file: Uploaded audio file (required)
        chat_id: Optional chat ID for conversation continuity
        current_user: Optional authenticated user
        db: Database session
        
    Returns:
        VoiceChatResponse with text reply and audio URL
        
    Raises:
        HTTPException: 400 for invalid input, 500 for processing failures
    """
    # 1. Input validation
    if not audio_file:
        raise HTTPException(status_code=400, detail="Audio file is required")
    
    # Read audio file as bytes
    try:
        audio_bytes = audio_file.file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded audio file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to read audio file") from e
    
    # Validate file is not empty
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    
    # Get original filename (for extension preservation)
    original_filename = audio_file.filename or "audio.wav"
    
    # 2. Save input audio
    try:
        input_audio_url = save_input_audio(audio_bytes, original_filename)
        # Extract filesystem path from URL (e.g., "/static/audio/xxx.wav" -> "static/audio/xxx.wav")
        input_audio_path = input_audio_url.lstrip("/")
    except ValueError as e:
        logger.error(f"Invalid audio file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid audio file: {str(e)}")
    except OSError as e:
        logger.error(f"Failed to save input audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save input audio")
    
    # 3. Speech-to-text (STT)
    try:
        voice_agent = GrokVoiceAgent()
        transcribed_text = voice_agent.transcribe_audio(input_audio_path)
        
        if not transcribed_text or not transcribed_text.strip():
            raise HTTPException(
                status_code=500,
                detail="Transcription returned empty result"
            )
    except FileNotFoundError as e:
        logger.error(f"Audio file not found after save: {str(e)}")
        raise HTTPException(status_code=500, detail="Audio file not found after save")
    except RuntimeError as e:
        logger.error(f"STT transcription failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Speech-to-text transcription failed")
    except Exception as e:
        logger.error(f"Unexpected STT error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Speech-to-text processing failed")
    
    # 4. Text LLM integration
    # Note: chat_id is passed but generate_reply() currently doesn't use conversation history
    # This is a known limitation documented in the intake report
    try:
        reply_data = generate_reply(transcribed_text)
        llm_text = reply_data.get("text", "")
        
        if not llm_text or not llm_text.strip():
            raise HTTPException(
                status_code=500,
                detail="LLM returned empty reply"
            )
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Text generation failed")
    
    # 5. Text-to-speech (TTS)
    try:
        # Use default voice configuration (None = API defaults)
        audio_bytes = voice_agent.synthesize_speech(llm_text, voice_config=None)
        
        if not audio_bytes:
            raise HTTPException(
                status_code=500,
                detail="TTS synthesis returned empty audio"
            )
    except ValueError as e:
        logger.error(f"Invalid TTS input: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid TTS input: {str(e)}")
    except RuntimeError as e:
        logger.error(f"TTS synthesis failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Text-to-speech synthesis failed")
    except Exception as e:
        logger.error(f"Unexpected TTS error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Text-to-speech processing failed")
    
    # 6. Save output audio
    try:
        # Default format is wav (can be made configurable later)
        audio_url = save_output_audio(audio_bytes, format="wav")
        # Ensure audio_url starts with / (root-relative, absolute path)
        # Return exactly as-is from audio_store - do not modify, prefix, or wrap
        if not audio_url.startswith("/"):
            raise RuntimeError(f"Audio URL must be root-relative path starting with /: {audio_url}")
    except ValueError as e:
        logger.error(f"Invalid audio format: {str(e)}")
        raise HTTPException(status_code=500, detail="Invalid audio format")
    except OSError as e:
        logger.error(f"Failed to save output audio: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save output audio")
    except RuntimeError as e:
        logger.error(f"Audio URL validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save output audio")
    
    # 7. Return response
    # Return audio_url exactly as produced by audio_store (root-relative path starting with /)
    return VoiceChatResponse(
        text=llm_text,
        audio_url=audio_url
    )


@router.post("/transcribe", response_model=VoiceResponse)
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Transcribe audio to text using STT."""
    # TODO: Implement STT logic
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/synthesize", response_model=VoiceResponse)
async def synthesize_speech(
    request: VoiceRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Synthesize text to speech using TTS."""
    # TODO: Implement TTS logic
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{job_id}", response_model=VoiceJobStatus)
async def get_voice_job(
    job_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get the status of a voice processing job."""
    # TODO: Implement job status check
    raise HTTPException(status_code=501, detail="Not implemented")

