from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from auth.models import User, get_db
from auth.security import decode_access_token

security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if credentials is None:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        return None
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        return None
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except Exception:
        return None

