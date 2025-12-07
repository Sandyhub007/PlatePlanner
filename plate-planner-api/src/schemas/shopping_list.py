"""Pydantic schemas for shopping lists - Phase 3"""

from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# ===== Shopping List Item Schemas =====

class ShoppingListItemBase(BaseModel):
    """Base schema for shopping list item"""
    ingredient_name: str = Field(..., min_length=1, max_length=255)
    normalized_name: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=50)
    category: str = Field("Other", max_length=100)
    estimated_price: Optional[float] = Field(None, ge=0)
    store_prices: Optional[Dict[str, float]] = None
    is_purchased: bool = False
    is_manual: bool = False
    recipe_references: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ShoppingListItemCreate(BaseModel):
    """Schema for creating a manual shopping list item"""
    ingredient_name: str = Field(..., min_length=1, max_length=255)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field("Other", max_length=100)
    notes: Optional[str] = None


class ShoppingListItemUpdate(BaseModel):
    """Schema for updating a shopping list item"""
    ingredient_name: Optional[str] = Field(None, min_length=1, max_length=255)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=100)
    is_purchased: Optional[bool] = None
    notes: Optional[str] = None


class ShoppingListItem(ShoppingListItemBase):
    """Full shopping list item schema with DB fields"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    list_id: UUID
    created_at: datetime
    updated_at: datetime


# ===== Shopping List Schemas =====

class ShoppingListBase(BaseModel):
    """Base schema for shopping list"""
    name: str = Field("Shopping List", max_length=255)
    status: str = Field("active", pattern="^(active|completed|archived)$")
    total_estimated_cost: float = Field(0.0, ge=0)
    total_items: int = Field(0, ge=0)
    purchased_items: int = Field(0, ge=0)


class ShoppingListGenerateRequest(BaseModel):
    """Schema for generating shopping list from meal plan"""
    plan_id: UUID
    name: Optional[str] = Field(None, max_length=255)
    include_price_comparison: bool = False
    exclude_items: List[str] = Field(default_factory=list, description="Items to exclude (e.g., pantry staples)")


class ShoppingListCreate(BaseModel):
    """Schema for creating a manual shopping list"""
    name: str = Field("Shopping List", max_length=255)
    plan_id: Optional[UUID] = None


class ShoppingListUpdate(BaseModel):
    """Schema for updating shopping list metadata"""
    name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, pattern="^(active|completed|archived)$")


class ShoppingList(ShoppingListBase):
    """Full shopping list schema with DB fields"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    plan_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    items: List[ShoppingListItem] = Field(default_factory=list)


class ShoppingListSummary(BaseModel):
    """Summary schema for listing shopping lists"""
    id: UUID
    name: str
    status: str
    total_items: int
    purchased_items: int
    total_estimated_cost: float
    created_at: datetime
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 0.0
        return round((self.purchased_items / self.total_items) * 100, 1)


class ShoppingListWithCategories(BaseModel):
    """Shopping list with items grouped by category"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    plan_id: Optional[UUID] = None
    name: str
    status: str
    total_estimated_cost: float
    total_items: int
    purchased_items: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    items_by_category: Dict[str, List[ShoppingListItem]] = Field(default_factory=dict)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 0.0
        return round((self.purchased_items / self.total_items) * 100, 1)


class ShoppingListPagination(BaseModel):
    """Paginated shopping list response"""
    items: List[ShoppingListSummary]
    total: int
    limit: int
    offset: int
    has_more: bool

