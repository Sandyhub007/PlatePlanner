from pydantic import BaseModel, UUID4, AnyHttpUrl
from typing import Optional, List
from datetime import datetime, date

class UserMealBase(BaseModel):
    meal_type: str
    meal_date: date
    title: Optional[str] = None
    calories: Optional[int] = None

class UserMealCreate(UserMealBase):
    pass

class UserMealInDB(UserMealBase):
    id: UUID4
    user_id: UUID4
    image_url: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserMealResponse(UserMealInDB):
    pass
