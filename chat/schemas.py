from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatCreate(BaseModel):
    title: str

class ChatOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    sender: str  # "user" or "maya"
    image_url: Optional[str] = None
    image_job_id: Optional[str] = None
    video_url: Optional[str] = None
    video_job_id: Optional[str] = None

class MessageOut(BaseModel):
    id: str
    chat_id: str
    sender: str
    content: str
    image_url: Optional[str] = None
    image_job_id: Optional[str] = None
    video_url: Optional[str] = None
    video_job_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatWithMessages(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []
    has_more: Optional[bool] = None
    total_messages: Optional[int] = None
    
    class Config:
        from_attributes = True

