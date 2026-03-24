from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MessageBase(BaseModel):
    match_id: Optional[str] = None
    type: str
    text: str


class MessageCreate(MessageBase):
    pass


class MessageRead(MessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime


class MessageUpdate(BaseModel):
    match_id: Optional[str] = None
    type: Optional[str] = None
    text: Optional[str] = None
