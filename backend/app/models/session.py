from pydantic import BaseModel
from typing import Optional


class SessionCreate(BaseModel):
    xianyu_account_id: int
    chat_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    item_id: Optional[str] = None


class SessionUpdate(BaseModel):
    last_message_time: Optional[int] = None


class SessionResponse(BaseModel):
    id: int
    xianyu_account_id: int
    chat_id: str
    user_id: Optional[str]
    user_name: Optional[str]
    item_id: Optional[str]
    last_message_time: Optional[int]
    created_at: int
    updated_at: int
