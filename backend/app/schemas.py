"""Pydantic request/response models (the API's public contract)."""
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
    visibilities: list[VisibilityOut]

    model_config = ConfigDict(from_attributes=True)


class VisibilityUpdateRequest(BaseModel):
    metric: str
    is_public: bool


class LeaderboardEntry(BaseModel):
    username: str
    value: float
    is_you: bool = False
    
