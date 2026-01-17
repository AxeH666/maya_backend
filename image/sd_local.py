import uuid
import asyncio
import shutil
import logging
from pathlib import Path
from typing import Optional

import httpx

from image.base import ImageProvider, ImageJob
from image.polling import (
    create_job,
    get_job,
    mark_job_processing,
    mark_job_ready,
    mark_job_failed,
)

logger = logging.getLogger(__name__)

# ================================
# CONFIG
# ================================

COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_OUTPUT_DIR = Path.home() / "ComfyUI" / "output"

STATIC_DIR = Path(__file__).parent.parent / "static" / "images"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


# ================================
# PROVIDER
# ================================


class SDLocalImageProvider(ImageProvider):
    """
    ComfyUI-based Stable Diffusion provider.
    Uses a fixed, validated ComfyUI workflow JSON.
    """

    def __init__(self):
        self.provider_name = "sd_local"
        logger.info("Initialized SDLocalImageProvider (ComfyUI direct)")

    async def create_image(self, prompt: str, user_id: Optional[str] = None) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        job_id = str(uuid.uuid4())
        create_job(job_id, provider=self.provider_name, user_id=user_id)
        mark_job_processing(job_id)

        asyncio.create_task(self._run_comfyui(job_id, prompt))
        return job_id

    # ================================
    # CORE LOGIC
    # ================================

    async def _run_comfyui(self, job_id: str, prompt: str):
        try:
            workflow = self._load_and_patch_workflow(prompt)

            payload = {
                "prompt": workflow,
                "client_id": job_id,
            }

            logger.info(f"[SD] Sending workflow to ComfyUI for job {job_id}")

            async with httpx.AsyncClient(timeout=300) as client:
                r = await client.post(COMFYUI_API_URL, json=payload)

            if r.status_code != 200:
                logger.error(f"[SD] ComfyUI error {r.status_code}: {r.text}")
                mark_job_failed(job_id)
                return

            image_path = await self._wait_for_output()

            if not image_path:
                logger.error("[SD] No image produced")
                mark_job_failed(job_id)
                return

            final_path = STATIC_DIR / f"maya_{job_id}.png"
            shutil.copy2(image_path, final_path)

            mark_job_ready(job_id, f"/static/images/{final_path.name}")
            logger.info(f"[SD] Job {job_id} completed")

        except Exception as e:
            logger.exception("[SD] Unexpected error")
            mark_job_failed(job_id)

    # ================================
    # WORKFLOW PATCHING
    # ================================

    def _load_and_patch_workflow(self, prompt: str) -> dict:
        """
        Build ComfyUI API prompt format with correct schema.
        Uses class_type, inputs, and string node IDs as keys.
        """
        # Default values
        negative_prompt = ""
        width = 512
        height = 768
        steps = 30
        cfg = 8.0
        seed = int(uuid.uuid4().int % (2**63))
        
        # Build ComfyUI API prompt format
        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "realisticVisionV60B1_v51VAE.safetensors"
                }
            },
            "2": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["1", 1],
                    "text": prompt
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["1", 1],
                    "text": negative_prompt or ""
                }
            },
            "4": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "seed": seed if seed > 0 else 0,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1.0
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                }
            },
            "7": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["6", 0],
                    "filename_prefix": "maya"
                }
            }
        }
        
        return workflow

    # ================================
    # OUTPUT POLLING
    # ================================

    async def _wait_for_output(
        self, timeout: int = 300, poll_interval: float = 1.5
    ) -> Optional[Path]:
        import time
        
        # Snapshot existing files BEFORE generation
        existing_files = {p.name for p in COMFYUI_OUTPUT_DIR.glob("*.png")} if COMFYUI_OUTPUT_DIR.exists() else set()
        start_time = time.time()

        logger.info(f"[SD] Waiting for new ComfyUI output (existing files: {len(existing_files)})")

        while time.time() - start_time < timeout:
            if not COMFYUI_OUTPUT_DIR.exists():
                await asyncio.sleep(poll_interval)
                continue
                
            current_files = list(COMFYUI_OUTPUT_DIR.glob("*.png"))
            
            # Only consider NEW files
            new_files = [p for p in current_files if p.name not in existing_files]
            
            if new_files:
                newest = max(new_files, key=lambda p: p.stat().st_mtime)
                logger.info(f"[SD] New ComfyUI output detected: {newest}")
                return newest
            
            await asyncio.sleep(poll_interval)

        logger.warning("[SD] Timeout waiting for ComfyUI output")
        return None

    # ================================
    # STATUS
    # ================================

    async def check_status(self, job_id: str) -> ImageJob:
        job = get_job(job_id)
        if not job:
            raise ValueError("Job not found")
        return job
