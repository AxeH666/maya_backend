from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from core.video import should_generate_video, generate_video_stub

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from prompts.system import MAYA_SYSTEM_PROMPT

client = OpenAI()

def generate_reply(user_input: str) -> dict:
    messages = [
        {"role": "system", "content": MAYA_SYSTEM_PROMPT},
        {"role": "user", "content": user_input}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
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
