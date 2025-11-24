from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

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
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- User Response ---
class User(UserBase):
    id: UUID
    is_active: bool
    is_premium: bool
    created_at: datetime
    preferences: Optional[UserPreferences] = None

    class Config:
        from_attributes = True

# --- Token ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

