from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# --- ObjectivePreferences ---

class ObjectivePreferencesBase(BaseModel):
    user_id: str
    bedroom_type: str
    selected_areas: List[str] = []
    min_budget: int
    max_budget: int
    move_in_date: date
    move_out_date: Optional[date] = None
    lease_length_months: Optional[int] = None
    laundry: List[str] = []
    parking: List[str] = []
    pets: bool = False
    work_latitude: Optional[float] = None
    work_longitude: Optional[float] = None
    commute_method: Optional[str] = None
    max_commute_minutes: Optional[int] = None


class ObjectivePreferencesCreate(ObjectivePreferencesBase):
    pass


class ObjectivePreferencesRead(ObjectivePreferencesBase):
    model_config = ConfigDict(from_attributes=True)

    id: str


class ObjectivePreferencesUpdate(BaseModel):
    bedroom_type: Optional[str] = None
    selected_areas: Optional[List[str]] = None
    min_budget: Optional[int] = None
    max_budget: Optional[int] = None
    move_in_date: Optional[date] = None
    move_out_date: Optional[date] = None
    lease_length_months: Optional[int] = None
    laundry: Optional[List[str]] = None
    parking: Optional[List[str]] = None
    pets: Optional[bool] = None
    work_latitude: Optional[float] = None
    work_longitude: Optional[float] = None
    commute_method: Optional[str] = None
    max_commute_minutes: Optional[int] = None


# --- SubjectivePreferences ---

class SubjectivePreferencesBase(BaseModel):
    user_id: str
    priority_focus: Optional[str] = None
    image_labels: List[str] = []
    neighborhood_labels: List[str] = []


class SubjectivePreferencesCreate(SubjectivePreferencesBase):
    pass


class SubjectivePreferencesRead(SubjectivePreferencesBase):
    model_config = ConfigDict(from_attributes=True)

    id: str


class SubjectivePreferencesUpdate(BaseModel):
    priority_focus: Optional[str] = None
    image_labels: Optional[List[str]] = None
    neighborhood_labels: Optional[List[str]] = None


# --- NegotiationPreferences ---

class NegotiationPreferencesBase(BaseModel):
    user_id: str
    enable_automation: bool = False
    negotiable_items: List[str] = []
    goals: List[str] = []
    max_rent: Optional[int] = None
    max_deposit: Optional[int] = None
    latest_move_in_date: Optional[date] = None
    min_lease_months: Optional[int] = None
    max_lease_months: Optional[int] = None
    negotiation_style: Optional[str] = None


class NegotiationPreferencesCreate(NegotiationPreferencesBase):
    pass


class NegotiationPreferencesRead(NegotiationPreferencesBase):
    model_config = ConfigDict(from_attributes=True)

    id: str


class NegotiationPreferencesUpdate(BaseModel):
    enable_automation: Optional[bool] = None
    negotiable_items: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    max_rent: Optional[int] = None
    max_deposit: Optional[int] = None
    latest_move_in_date: Optional[date] = None
    min_lease_months: Optional[int] = None
    max_lease_months: Optional[int] = None
    negotiation_style: Optional[str] = None


# --- NotificationPreferences ---

class NotificationPreferencesBase(BaseModel):
    user_id: str
    enable_notifications: bool = True
    auto_scheduling: bool = False
    notification_types: List[str] = []
    frequency: str = "realtime"


class NotificationPreferencesCreate(NotificationPreferencesBase):
    pass


class NotificationPreferencesRead(NotificationPreferencesBase):
    model_config = ConfigDict(from_attributes=True)

    id: str


class NotificationPreferencesUpdate(BaseModel):
    enable_notifications: Optional[bool] = None
    auto_scheduling: Optional[bool] = None
    notification_types: Optional[List[str]] = None
    frequency: Optional[str] = None
