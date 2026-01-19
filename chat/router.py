from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from auth.models import get_db, User
from auth.deps import get_current_user_optional
from chat.models import Chat, Message
from chat.schemas import ChatCreate, ChatOut, MessageCreate, MessageOut, ChatWithMessages
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=ChatOut)
async def create_chat(
    chat_data: ChatCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Create a new chat conversation."""
    chat = Chat(
        title=chat_data.title,
        user_id=current_user.id if current_user else None
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    logger.info(f"Created chat {chat.id} for user {current_user.id if current_user else 'anonymous'}")
    return chat


@router.get("", response_model=List[ChatOut])
async def list_chats(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all chats for the current user (or anonymous chats)."""
    query = db.query(Chat)
    
    if current_user:
        query = query.filter(Chat.user_id == current_user.id)
    else:
        query = query.filter(Chat.user_id.is_(None))
    
    chats = query.order_by(Chat.updated_at.desc()).offset(offset).limit(limit).all()
    return chats


@router.get("/{chat_id}", response_model=ChatWithMessages)
async def get_chat(
    chat_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get a chat with its messages (with pagination for scroll-to-load)."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check ownership (users can only access their own chats, anonymous chats are accessible)
    if chat.user_id and current_user and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if chat.user_id and not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")
    
    # Get messages with pagination
    # offset: Number of messages already loaded (starting from newest)
    # offset=0: Get latest messages (for initial load)
    # offset>0: Get older messages (for scroll-up pagination)
    messages_query = db.query(Message).filter(Message.chat_id == chat_id)
    total_messages = messages_query.count()
    
    logger.info(f"Getting messages for chat {chat_id}, offset={offset}, limit={limit}, total={total_messages}")
    
    if offset == 0:
        # Initial load: Get latest messages (newest first, then reverse for chronological display)
        messages = messages_query.order_by(Message.created_at.desc()).limit(limit).all()
        messages = list(reversed(messages))  # Reverse to show oldest to newest
        logger.info(f"Initial load: Got {len(messages)} messages (latest), total={total_messages}")
    else:
        # Scroll-up: Get older messages (skip 'offset' messages from newest, then get next 'limit' older)
        # Order by desc to get from newest, skip offset, take limit, then reverse
        messages = messages_query.order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
        messages = list(reversed(messages))  # Reverse to show oldest to newest
        logger.info(f"Scroll-up load: Got {len(messages)} older messages at offset {offset}, total={total_messages}")
    
    # Check if there are more messages beyond what we're returning
    has_more = total_messages > (offset + len(messages))
    
    return ChatWithMessages(
        id=chat.id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[MessageOut.model_validate(msg) for msg in messages],
        has_more=has_more,
        total_messages=total_messages
    )


@router.post("/{chat_id}/messages", response_model=MessageOut)
async def create_message(
    chat_id: str,
    message_data: MessageCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Add a message to a chat."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check ownership
    if chat.user_id and current_user and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if chat.user_id and not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")
    
    message = Message(
        chat_id=chat_id,
        sender=message_data.sender,
        content=message_data.content,
        image_url=message_data.image_url,
        image_job_id=message_data.image_job_id,
        video_url=message_data.video_url,
        video_job_id=message_data.video_job_id
    )
    db.add(message)
    
    # Update chat's updated_at timestamp
    from datetime import datetime
    chat.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    logger.info(f"Added message {message.id} to chat {chat_id}")
    return message


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Delete a chat and all its messages."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Check ownership
    if chat.user_id and current_user and chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    if chat.user_id and not current_user:
        raise HTTPException(status_code=403, detail="Authentication required")
    
    db.delete(chat)
    db.commit()
    logger.info(f"Deleted chat {chat_id}")
    return {"status": "deleted"}

