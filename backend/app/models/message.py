from pydantic import BaseModel
from typing import Optional


class MessageCreate(BaseModel):
    session_id: int
    xianyu_account_id: int
    is_outgoing: bool = False
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    content: str
    message_type: str = "chat"


class MessageResponse(BaseModel):
    id: int
    session_id: int
    xianyu_account_id: int
    is_outgoing: bool
    sender_id: Optional[str]
    sender_name: Optional[str]
    content: str
    message_type: str
    created_at: int
    send_status: Optional[str] = None  # "sent" / "failed" / None
