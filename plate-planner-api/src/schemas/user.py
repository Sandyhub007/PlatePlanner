from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Shared Properties ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


# --- User Registration ---
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


# --- User Preferences ---
class UserPreferencesBase(BaseModel):
    dietary_restrictions: List[str] = []
    allergies: List[str] = []
    cuisine_preferences: List[str] = []
    calorie_target: Optional[int] = None
    protein_target: Optional[int] = None
    carb_target: Optional[int] = None
    fat_target: Optional[int] = None
    cooking_time_max: Optional[int] = None
    budget_per_week: Optional[float] = None
    people_count: int = 1


class UserPreferencesCreate(UserPreferencesBase):
    pass


class UserPreferencesUpdate(UserPreferencesBase):
    pass


class UserPreferences(UserPreferencesBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


# --- User Response ---
class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    is_premium: bool
    auth_provider: str = "email"
    profile_photo_url: Optional[str] = None
    created_at: datetime
    preferences: Optional[UserPreferences] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    profile_photo_url: Optional[str] = None

# --- Token ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    id_token: Optional[str] = None
    access_token: Optional[str] = None


