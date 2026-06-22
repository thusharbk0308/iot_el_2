from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

# --- AUTH SCHEMAS ---

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[str] = "user"

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- BUSINESS LOGIC SCHEMAS ---

class AccessLogResponse(BaseModel):
    id: int
    timestamp: datetime
    name: str
    status: str
    confidence: float
    signal_sent: str
    
    class Config:
        orm_mode = True

class IntruderAlertResponse(BaseModel):
    id: int
    timestamp: datetime
    snapshot_path: str
    email_sent: bool
    
    class Config:
        orm_mode = True

class AuthorizedUserResponse(BaseModel):
    id: int
    name: str
    image_count: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class NotificationResponse(BaseModel):
    id: int
    timestamp: datetime
    message: str
    type: str
    is_read: bool
    
    class Config:
        orm_mode = True

class SystemStatusResponse(BaseModel):
    pi: str
    camera: str
    ai_server: str
    lock: str
    database: str

class LockControlRequest(BaseModel):
    action: str # "unlock" or "lock"
