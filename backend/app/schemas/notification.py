from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationBase(BaseModel):
    user_id: str
    content: str
    type: str
    read: bool = False


class NotificationCreate(NotificationBase):
    pass


class NotificationRead(NotificationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime


class NotificationUpdate(BaseModel):
    content: Optional[str] = None
    type: Optional[str] = None
    read: Optional[bool] = None
