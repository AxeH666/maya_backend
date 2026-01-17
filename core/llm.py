from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from core.video import should_generate_video, generate_video_stub
import os

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from prompts.system import MAYA_SYSTEM_PROMPT

api_key = os.getenv("GROK_API_KEY")
if api_key:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1"
    )
else:
    client = None


def generate_reply(user_input: str) -> dict:
    if client is None:
        return {
            "text": "Grok API key not configured. Please set GROK_API_KEY environment variable.",
            "video": None
        }
    
    messages = [
        {"role": "system", "content": MAYA_SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    response = client.chat.completions.create(
        model="grok-3",
        messages=messages,
        temperature=0.7
    )

    text_reply = response.choices[0].message.content

    video_url = None
    if should_generate_video(user_input):
        video_url = generate_video_stub()

    return {
        "text": text_reply,
        "video": video_url
    }
