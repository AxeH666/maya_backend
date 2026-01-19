# MAYA Frontend Integration Guide

This document describes how to integrate the MAYA frontend with the MAYA backend and ComfyUI services.

## Architecture Overview

```
Frontend (React/Next.js) → Backend (FastAPI) → ComfyUI (Stable Diffusion)
     ↓                           ↓
  Audio Playback          Whisper STT
                          Grok LLM
                          ElevenLabs TTS
                          Static Files (/static/*)
```

**Critical Rule:** Frontend **NEVER** talks directly to ComfyUI. All communication goes through the backend.

## Service URLs

- **Backend:** `http://127.0.0.1:8000`
- **Frontend:** `http://127.0.0.1:3000` (or `http://localhost:3000`)
- **ComfyUI:** `http://127.0.0.1:8188` (internal, not accessed by frontend)

## Step 1: API Base Configuration

### Environment Variable

Create a `.env.local` file (or `.env` depending on your framework):

```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

### API Client Setup

Create a centralized API client module:

```typescript
// lib/api.ts or utils/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000';

// NOTE:
// Backend returns root-relative static URLs (/static/...)
// These must be prefixed with API_BASE at runtime.
// Do NOT modify paths returned by backend.

export const apiBase = API_BASE;

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    if (response.status >= 400 && response.status < 500) {
      const error = await response.json().catch(() => ({ detail: 'Client error' }));
      throw new Error(error.detail || `Request failed: ${response.status}`);
    } else {
      throw new Error(`Server error: ${response.status}`);
    }
  }

  return response.json();
}
```

## Step 2: Voice Chat Integration

### Recording Audio

```typescript
// hooks/useVoiceChat.ts or components/VoiceChat.tsx

async function recordAudio(): Promise<Blob> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream, {
    mimeType: 'audio/webm;codecs=opus', // or 'audio/wav'
  });

  return new Promise((resolve, reject) => {
    const chunks: Blob[] = [];
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      stream.getTracks().forEach(track => track.stop());
      const blob = new Blob(chunks, { type: 'audio/webm' });
      resolve(blob);
    };

    mediaRecorder.onerror = reject;

    mediaRecorder.start();
    
    // Stop after 5 seconds (or use button click)
    setTimeout(() => mediaRecorder.stop(), 5000);
  });
}
```

### Sending Audio to Backend

```typescript
// hooks/useVoiceChat.ts

interface VoiceChatResponse {
  text: string;
  audio_url: string; // e.g., "/static/audio/xyz.wav"
}

async function sendVoiceChat(audioBlob: Blob, chatId?: string): Promise<VoiceChatResponse> {
  const formData = new FormData();
  formData.append('audio_file', audioBlob, 'audio.webm');
  if (chatId) {
    formData.append('chat_id', chatId);
  }

  const response = await fetch(`${apiBase}/voice/chat`, {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type header - browser sets it with boundary
  });

  if (!response.ok) {
    if (response.status >= 400 && response.status < 500) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || 'Voice chat request failed');
    } else {
      throw new Error('Server error. Please try again.');
    }
  }

  return response.json();
}
```

### Playing Audio Response

```typescript
// hooks/useVoiceChat.ts

function playAudio(audioUrl: string): Promise<void> {
  return new Promise((resolve, reject) => {
    // NOTE: Backend returns root-relative paths like "/static/audio/xyz.wav"
    // Must prefix with API_BASE to create full URL
    const fullUrl = `${apiBase}${audioUrl}`;
    
    const audio = new Audio(fullUrl);
    
    audio.onended = () => resolve();
    audio.onerror = (error) => {
      console.error('Audio playback failed:', error);
      reject(new Error('Failed to play audio'));
    };
    
    audio.play().catch(reject);
  });
}

// Usage in component
async function handleVoiceChat() {
  try {
    setLoading(true);
    setError(null);
    
    // Record audio
    const audioBlob = await recordAudio();
    
    // Send to backend
    const response = await sendVoiceChat(audioBlob, currentChatId);
    
    // Display text
    setResponseText(response.text);
    
    // Play audio automatically
    await playAudio(response.audio_url);
    
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Voice chat failed');
  } finally {
    setLoading(false);
  }
}
```

## Step 3: Image Generation Integration

### Requesting Images

```typescript
// hooks/useImageGeneration.ts

interface ImageGenerateRequest {
  prompt: string;
  negative_prompt?: string;
  width?: number;
  height?: number;
  steps?: number;
  cfg?: number;
  seed?: number;
}

interface ImageGenerateResponse {
  job_id: string;
  status: string;
}

async function generateImage(request: ImageGenerateRequest): Promise<ImageGenerateResponse> {
  return apiRequest<ImageGenerateResponse>('/maya/image', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
```

### Polling Image Job Status

```typescript
// hooks/useImageGeneration.ts

interface ImageJobStatus {
  status: 'pending' | 'processing' | 'ready' | 'failed' | 'not_found';
  image_url?: string; // e.g., "/static/images/xyz.png"
}

async function getImageJobStatus(jobId: string): Promise<ImageJobStatus> {
  return apiRequest<ImageJobStatus>(`/image/${jobId}`);
}

// Poll until ready
async function waitForImage(jobId: string, maxAttempts = 30): Promise<string> {
  for (let i = 0; i < maxAttempts; i++) {
    const status = await getImageJobStatus(jobId);
    
    if (status.status === 'ready' && status.image_url) {
      return status.image_url;
    }
    
    if (status.status === 'failed') {
      throw new Error('Image generation failed');
    }
    
    // Wait 1 second before next poll
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  throw new Error('Image generation timed out');
}
```

### Displaying Images

```typescript
// components/ImageDisplay.tsx

function ImageDisplay({ imageUrl }: { imageUrl: string }) {
  // NOTE: Backend returns root-relative paths like "/static/images/xyz.png"
  // Must prefix with API_BASE to create full URL
  const fullUrl = `${apiBase}${imageUrl}`;
  
  return (
    <img 
      src={fullUrl} 
      alt="Generated image"
      onError={(e) => {
        console.error('Failed to load image:', imageUrl);
        e.currentTarget.style.display = 'none';
      }}
    />
  );
}
```

## Step 4: Text Chat Integration

```typescript
// hooks/useChat.ts

interface ChatRequest {
  message: string;
  image_generation?: boolean;
  video_generation?: boolean;
  chat_id?: string;
}

interface ChatResponse {
  text: string;
  video_job_id?: string;
  image_job_id?: string;
  chat_id?: string;
}

async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return apiRequest<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
```

## Step 5: Error Handling

### Error Types

```typescript
// lib/errors.ts

export class APIError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export function handleAPIError(error: unknown): string {
  if (error instanceof APIError) {
    if (error.statusCode >= 400 && error.statusCode < 500) {
      return error.message || 'Invalid request. Please check your input.';
    } else {
      return 'Server error. Please try again later.';
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
}
```

### Graceful Degradation

```typescript
// components/VoiceChat.tsx

function VoiceChat() {
  const [error, setError] = useState<string | null>(null);
  const [audioError, setAudioError] = useState(false);

  async function handleVoiceChat() {
    try {
      setError(null);
      setAudioError(false);
      
      const response = await sendVoiceChat(audioBlob);
      
      // Always show text, even if audio fails
      setResponseText(response.text);
      
      // Try to play audio, but don't crash if it fails
      try {
        await playAudio(response.audio_url);
      } catch (audioErr) {
        console.warn('Audio playback failed:', audioErr);
        setAudioError(true);
        // UI can show "Audio unavailable" message
      }
      
    } catch (err) {
      const message = handleAPIError(err);
      setError(message);
      // Don't crash - show error message to user
    }
  }

  return (
    <div>
      {error && <div className="error">{error}</div>}
      {audioError && <div className="warning">Audio unavailable</div>}
      {/* Rest of UI */}
    </div>
  );
}
```

## Step 6: Static File URL Handling

### Important Contract

**Backend returns root-relative paths:**
- Audio: `/static/audio/<filename>.wav`
- Images: `/static/images/<filename>.png`

**Frontend must prefix with API_BASE:**
```typescript
// ✅ CORRECT
const audioUrl = `${apiBase}${response.audio_url}`;
const imageUrl = `${apiBase}${response.image_url}`;

// ❌ WRONG - Don't modify the path
const audioUrl = `/voice${response.audio_url}`;
const audioUrl = response.audio_url.replace('/static', '/voice/static');
```

### Helper Function

```typescript
// lib/api.ts

/**
 * Converts a root-relative static file URL to a full URL.
 * Backend returns paths like "/static/audio/xyz.wav"
 * This function prefixes with API_BASE.
 */
export function getStaticUrl(relativePath: string): string {
  if (!relativePath.startsWith('/')) {
    throw new Error(`Invalid static path: ${relativePath} (must start with /)`);
  }
  return `${apiBase}${relativePath}`;
}

// Usage
const audioUrl = getStaticUrl(response.audio_url);
const imageUrl = getStaticUrl(response.image_url);
```

## Complete Example: Voice Chat Component

```typescript
// components/VoiceChat.tsx

import { useState } from 'react';
import { apiBase, getStaticUrl } from '@/lib/api';

interface VoiceChatResponse {
  text: string;
  audio_url: string;
}

export function VoiceChat() {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [responseText, setResponseText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);

      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        const blob = new Blob(chunks, { type: 'audio/webm' });
        await sendVoiceChat(blob);
      };

      recorder.start();
      setMediaRecorder(recorder);
      setRecording(true);
    } catch (err) {
      setError('Failed to access microphone');
    }
  }

  function stopRecording() {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setRecording(false);
    }
  }

  async function sendVoiceChat(audioBlob: Blob) {
    setLoading(true);
    setError(null);
    setResponseText(null);

    try {
      const formData = new FormData();
      formData.append('audio_file', audioBlob, 'audio.webm');

      const response = await fetch(`${apiBase}/voice/chat`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `Request failed: ${response.status}`);
      }

      const data: VoiceChatResponse = await response.json();
      setResponseText(data.text);

      // Play audio
      const audioUrl = getStaticUrl(data.audio_url);
      const audio = new Audio(audioUrl);
      audio.play().catch((err) => {
        console.warn('Audio playback failed:', err);
        // Don't crash - just log warning
      });

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Voice chat failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button 
        onClick={recording ? stopRecording : startRecording}
        disabled={loading}
      >
        {recording ? 'Stop Recording' : 'Start Recording'}
      </button>

      {loading && <div>Processing...</div>}
      {error && <div className="error">{error}</div>}
      {responseText && <div>{responseText}</div>}
    </div>
  );
}
```

## Testing Checklist

- [ ] Frontend can call backend (CORS working)
- [ ] Backend accepts audio files
- [ ] Whisper STT transcribes audio correctly
- [ ] Grok LLM generates replies
- [ ] ElevenLabs TTS generates audio
- [ ] Audio auto-plays in frontend
- [ ] Images render when requested
- [ ] No direct ComfyUI calls from frontend
- [ ] Error handling works gracefully
- [ ] Static file URLs are constructed correctly

## Service Independence

Each service can restart independently:
- **Backend restart:** Frontend will retry failed requests
- **Frontend restart:** No impact on backend
- **ComfyUI restart:** Backend handles errors, frontend unaffected

No shared state except HTTP requests/responses.

