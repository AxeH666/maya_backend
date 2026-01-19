from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from core.video import should_generate_video, generate_video_stub
import os

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from prompts.system import MAYA_SYSTEM_PROMPT

# Verify GROK_API_KEY is available after .env loading
if "GROK_API_KEY" not in os.environ or not os.environ["GROK_API_KEY"]:
    raise RuntimeError(
        "GROK_API_KEY is required but not found in environment variables. "
        "Please set GROK_API_KEY in your .env file or environment."
    )

api_key = os.environ["GROK_API_KEY"]
client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)


def generate_reply(user_input: str) -> dict:
    
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
