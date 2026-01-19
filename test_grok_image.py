"""
Standalone test script for Grok image generation API.

This is for manual verification ONLY.
Do not import this file anywhere in the application.
"""
import requests
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("GROK_API_KEY_IMAGE") or os.getenv("GROK_API_KEY_image")

if not API_KEY:
    print("ERROR: GROK_API_KEY_IMAGE not found in environment")
    exit(1)

url = "https://api.x.ai/v1/images/generations"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "grok-2-image",
    "prompt": "A cinematic neon cyberpunk woman glowing purple light"
}

print(f"Testing Grok image generation...")
print(f"Endpoint: {url}")
print(f"Model: {payload['model']}")
print(f"Prompt: {payload['prompt']}")
print("-" * 50)

try:
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    
    print(f"STATUS: {response.status_code}")
    print(f"RESPONSE: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            if "url" in data["data"][0]:
                print(f"\nSUCCESS! Image URL: {data['data'][0]['url']}")
            else:
                print(f"\nERROR: Response missing 'url' field")
        else:
            print(f"\nERROR: Response missing 'data' array")
    else:
        print(f"\nERROR: API returned status {response.status_code}")
        
except Exception as e:
    print(f"ERROR: {str(e)}")


