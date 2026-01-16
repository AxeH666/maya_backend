import uuid
from core.video_store import create_job

def request_video(prompt: str) -> str:
    """
    Creates a video generation job and returns job_id.
    Actual provider integration comes later.
    """
    job_id = str(uuid.uuid4())
    create_job(job_id)
    return job_id


def should_generate_video(text: str) -> bool:
    """
    Decide whether this message deserves a video response.
    Keep this conservative.
    """
    triggers = [
        "show me",
        "i want to see",
        "make it visual",
        "can you show",
        "video",
        "lemme see",
        "let me see"
    ]
    return any(t in text.lower() for t in triggers)


def build_video_prompt() -> str:
    """
    Maya-controlled prompt.
    User input NEVER goes here directly.
    """
    return (
        "A cinematic, softly lit scene with a confident woman "
        "leaning slightly closer to the camera, playful smile, "
        "slow and graceful movement, warm lighting, intimate mood, "
        "romantic atmosphere, shallow depth of field"
    )


def generate_video_stub() -> str:
    """
    Temporary stub until real API is wired.
    """
    fake_id = uuid.uuid4().hex
    return f"https://example.com/video/{fake_id}.mp4"
