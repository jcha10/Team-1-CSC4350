"""Pydantic request/response models (the API's public contract)."""
import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token: str
    user: "UserOut"


class VisibilityOut(BaseModel):
    metric: str
    is_public: bool

    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    points: int
    apm: float
    total_clicks: int
    active_screen_time: float
    tasks_completed: int
    kudos_given: int
    current_streak: int
    longest_streak: int
    kudos_received: int
    visibilities: list[VisibilityOut]

    model_config = ConfigDict(from_attributes=True)


class VisibilityUpdateRequest(BaseModel):
    metric: str
    is_public: bool


class LeaderboardEntry(BaseModel):
    username: str
    value: float
    is_you: bool = False
    kudos_received: int = 0


class KudosResponse(BaseModel):
    to_username: str
    kudos_received: int


class TelemetryLogOut(BaseModel):
    id: int
    username: str
    timestamp: datetime.datetime
    raw_text: str
    matched_keyword: Optional[str]
    is_flagged: bool

    model_config = ConfigDict(from_attributes=True)


class DisloyaltyStat(BaseModel):
    username: str
    violation_count: int
    is_disloyal: bool


class EmployeeHrView(BaseModel):
    id: int
    username: str
    role: str
    points: int
    apm: float
    total_clicks: int
    active_screen_time: float
    tasks_completed: int
    kudos_given: int
    is_disloyal: bool
    disloyal_violation_count: int
    # HR sees this regardless of what the employee shows on the public
    # leaderboard - visibility settings only affect the peer-facing view.
    hidden_metrics: list[str]

    model_config = ConfigDict(from_attributes=True)


class TaskOut(BaseModel):
    id: int
    title: str
    is_done: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class TaskUpdateRequest(BaseModel):
    is_done: bool


class AnnouncementOut(BaseModel):
    id: int
    title: str
    body: str
    author_username: str
    created_at: datetime.datetime


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=2000)
