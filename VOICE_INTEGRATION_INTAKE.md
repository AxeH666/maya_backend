# MAYA Voice Integration Intake Report

## 1. MAYA Project Directory Tree

```
/home/axehe/maya/
├── app/
│   ├── __init__.py
│   └── main.py                    # FastAPI application entry point
├── auth/
│   ├── __init__.py
│   ├── deps.py                   # Authentication dependencies
│   ├── models.py                 # User database models (SQLAlchemy)
│   ├── router.py                 # Auth endpoints (/auth/signup, /auth/login)
│   ├── schemas.py                # Pydantic schemas for auth
│   └── security.py               # Password hashing, JWT token handling
├── chat/
│   ├── __init__.py
│   ├── models.py                 # Chat and Message database models
│   ├── router.py                 # Chat endpoints (/chats/*)
│   └── schemas.py                # Pydantic schemas for chat
├── core/
│   ├── __init__.py
│   ├── image.py                  # Legacy Grok image generation (unused)
│   ├── llm.py                    # LLM integration (Grok API calls)
│   ├── video.py                  # Video generation helpers
│   └── video_store.py            # Legacy video job store (unused)
├── image/
│   ├── __init__.py
│   ├── base.py                   # ImageProvider abstract interface
│   ├── factory.py                # Image provider factory
│   ├── grok.py                   # Grok image provider (unused)
│   ├── polling.py                # Image job state management (in-memory)
│   └── sd_local.py               # ComfyUI/Stable Diffusion local provider
├── prompts/
│   ├── __init__.py
│   └── system.py                 # MAYA system prompt
├── static/
│   └── images/                   # Generated image storage
├── video/
│   ├── __init__.py
│   ├── base.py                   # VideoProvider abstract interface
│   ├── factory.py                # Video provider factory
│   ├── mock.py                   # Mock video provider
│   ├── pika.py                   # Pika video provider
│   └── polling.py                # Video job state management (in-memory)
├── .gitignore
├── maya.db                       # SQLite database
└── test_grok_image.py            # Test script

UNKNOWN:
- Frontend directory (separate codebase, referenced via CORS at localhost:3000)
- Configuration files (requirements.txt, README.md, docker files)
- Scripts directory
- Services directory
- Agents directory
- Memory directory (memory logic is in chat/models.py)
```

## 2. Current LLM Stack

**Primary text LLM provider:** Grok (xAI)

**Model name(s):** `grok-3`

**Local or remote inference:** Remote (API-based)

**File(s) where LLM calls are made:** `/home/axehe/maya/core/llm.py`

**Is streaming enabled?** NO

**If streaming: method used:** N/A (streaming not implemented)

**Fallback model present?** NO (if GROK_API_KEY is missing, returns error message to user)

## 3. Persona Enforcement

**Is there a system prompt?** YES

**Prompt file location(s):** `/home/axehe/maya/prompts/system.py`

**Is persona enforced in:**

- **Prompt templates:** YES (system prompt contains full persona definition)
- **Backend logic:** NO (no post-processing or filtering logic)
- **Memory conditioning:** NO (no memory-based persona reinforcement)
- **Post-processing rules:** NO

**Is persona enforcement finalized?** YES (system prompt is complete and explicit)

## 4. Conversation & Memory Flow

**Is conversation state stored?** YES

**Memory type:** Short-term (database storage)

**Storage mechanism:** SQLite database (`maya.db`) via SQLAlchemy ORM

**File(s) handling memory logic:**
- `/home/axehe/maya/chat/models.py` - Database models (Chat, Message tables)
- `/home/axehe/maya/chat/router.py` - Chat retrieval endpoints
- `/home/axehe/maya/app/main.py` - Message persistence in `/chat` endpoint

**CRITICAL FINDING:** Conversation history is stored in database but **NOT passed to LLM**. The `generate_reply()` function in `core/llm.py` only receives the current user message. Previous messages from the chat are not loaded or included in the LLM context.

## 5. Current Input / Output Modalities

**Supported input types:** Text only

**Supported output types:** Text, Image (async job-based), Video (async job-based)

**Where input is handled (file/module):**
- `/home/axehe/maya/app/main.py` - `/chat` endpoint receives `ChatRequest` with `message: str`
- `/home/axehe/maya/core/llm.py` - `generate_reply(user_input: str)` processes text input

**Where output is rendered (file/module):**
- `/home/axehe/maya/app/main.py` - `/chat` endpoint returns JSON with `text`, `image_job_id`, `video_job_id`
- `/home/axehe/maya/app/main.py` - `/image/{job_id}` and `/video/{job_id}` endpoints return job status
- Frontend (separate codebase at localhost:3000) handles rendering

## 6. Desired Voice Integration (v1 Scope)

**Voice input required?** NOT DEFINED (user requirements not specified in codebase)

**Voice output required?** NOT DEFINED (user requirements not specified in codebase)

**Real-time streaming required?** NOT DEFINED (user requirements not specified in codebase)

**Acceptable latency:** NOT DEFINED

**Target platform(s):** NOT DEFINED (CORS configured for localhost:3000 suggests web, but not confirmed)

**Browser-based or native app?** NOT DEFINED (evidence suggests browser-based frontend, but not confirmed)

## 7. Groq API Constraints

**Groq API key already available?** NO (codebase uses Grok/xAI API, not Groq API. No Groq integration found)

**Allowed endpoints (STT / TTS / Both / Unknown):** UNKNOWN (Groq API not yet integrated)

**Firewall or network restrictions?** NOT DEFINED

**External streaming allowed?** NOT DEFINED

**Any explicit-content constraints?** NOT DEFINED (system prompt contains explicit sexual content, but API-level constraints unknown)

## 8. Non-Functional Constraints

**Performance priority (latency vs quality):** NOT DEFINED

**Scalability requirement (single user / multi-user):** PARTIAL (database supports multi-user via user_id, but no explicit scaling design documented)

**Offline fallback required?** NO (no offline capabilities implemented or planned)

**Logging required for voice?** NOT DEFINED (general logging exists via Python logging module, but voice-specific logging not specified)

## 9. Known Gaps / Risks

**Missing components:**
1. Voice input handling (STT) - completely absent
2. Voice output handling (TTS) - completely absent
3. Audio file upload/download endpoints - absent
4. Audio storage mechanism - absent
5. Groq API integration - absent (currently uses Grok/xAI)
6. Conversation context loading - messages stored but not passed to LLM
7. Streaming support - not implemented for text or voice
8. Frontend codebase - separate, unknown structure

**Architectural uncertainty:**
1. How to integrate Groq STT/TTS alongside existing Grok LLM
2. Whether to add audio endpoints to existing `/chat` endpoint or create new `/voice` endpoints
3. How to handle audio file storage (similar to image storage in `/static/images/`?)
4. Whether voice should be synchronous or async job-based (like images/videos)
5. How to handle real-time streaming if required (WebSocket vs SSE vs polling)

**Areas not yet designed:**
1. Voice input processing pipeline
2. Voice output generation pipeline
3. Audio format specifications (WAV, MP3, OGG, etc.)
4. Audio quality/bitrate settings
5. Voice activity detection (VAD)
6. Audio chunking for streaming
7. Error handling for audio generation failures

**Dependencies that block voice integration:**
1. Groq API key availability - NOT CONFIRMED
2. Groq API documentation/endpoint specifications - NOT REVIEWED
3. Frontend audio recording/playback capabilities - UNKNOWN
4. Network/firewall restrictions for Groq API - NOT DEFINED

## 10. Readiness Assessment

**Is MAYA ready for voice integration today?** PARTIAL

**What is the single biggest blocker, if any?**

The single biggest blocker is: **Conversation context is not passed to the LLM**. Currently, `generate_reply()` in `core/llm.py` only receives the current user message. For voice integration to work effectively, the system needs to:
1. Load previous messages from the chat when `chat_id` is provided
2. Build a proper message history array for the LLM API
3. Include conversation context in LLM calls

Without this, voice conversations will lack continuity and context awareness, making the integration incomplete.

**Additional blockers (secondary):**
- No Groq API integration exists (currently uses Grok/xAI)
- No audio handling infrastructure (endpoints, storage, processing)
- No streaming support (required for real-time voice)
- Frontend capabilities unknown (audio recording/playback)


