from datetime import datetime
from typing import List
from pydantic import BaseModel


class PantryItemResponse(BaseModel):
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class PantryResponse(BaseModel):
    items: List[PantryItemResponse]


class AddPantryItemsRequest(BaseModel):
    items: List[str]
