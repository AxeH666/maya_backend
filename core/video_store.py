from typing import Dict
from time import time

VIDEO_JOBS: Dict[str, dict] = {}

def create_job(job_id: str):
    VIDEO_JOBS[job_id] = {
        "status": "pending",
        "created_at": time(),
        "video_url": None
    }

def complete_job(job_id: str, video_url: str):
    if job_id in VIDEO_JOBS:
        VIDEO_JOBS[job_id]["status"] = "ready"
        VIDEO_JOBS[job_id]["video_url"] = video_url

def get_job(job_id: str):
    return VIDEO_JOBS.get(job_id)





