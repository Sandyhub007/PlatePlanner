from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class MealPlanItemBase(BaseModel):
    day_of_week: int
    meal_type: str
    recipe_id: str
    recipe_title: str
    servings: int
    calories: Optional[int] = None
    protein: Optional[int] = None
    carbs: Optional[int] = None
    fat: Optional[int] = None
    estimated_cost: Optional[float] = None
    prep_time_minutes: Optional[int] = None


class MealPlanItemCreate(MealPlanItemBase):
    pass


class MealPlanItem(MealPlanItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    created_at: datetime

class MealPlanBase(BaseModel):
    week_start_date: date
    week_end_date: date
    status: str = "draft"
    total_calories: int = 0
    total_protein: int = 0
    total_carbs: int = 0
    total_fat: int = 0
    total_estimated_cost: float = 0.0


class MealPlanPreferencesOverride(BaseModel):
    dietary_restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    cuisine_preferences: Optional[List[str]] = None
    calorie_target: Optional[int] = None
    protein_target: Optional[int] = None
    carb_target: Optional[int] = None
    fat_target: Optional[int] = None
    cooking_time_max: Optional[int] = None
    budget_per_week: Optional[float] = None
    people_count: Optional[int] = None

class MealPlanCreate(BaseModel):
    week_start_date: date
    preferences_override: Optional[MealPlanPreferencesOverride] = None


class MealPlanItemSwap(BaseModel):
    new_recipe_id: str


class MealPlanRegenerateRequest(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    preferences_override: Optional[MealPlanPreferencesOverride] = None


class RecipeAlternative(BaseModel):
    recipe_id: str
    title: str
    calories: int
    protein: int
    carbs: int
    fat: int
    estimated_cost: float
    prep_time_minutes: int


class ValidationSeverity(str, Enum):
    error = "error"
    warning = "warning"


class MealPlanValidationIssue(BaseModel):
    code: str
    severity: ValidationSeverity
    message: str


class MealPlanValidationResult(BaseModel):
    plan_id: UUID
    is_valid: bool
    issues: List[MealPlanValidationIssue] = Field(default_factory=list)


class MealNutritionTotals(BaseModel):
    calories: int
    protein: int
    carbs: int
    fat: int


class MealPlanDaySummary(BaseModel):
    day_index: int
    date: date
    total: MealNutritionTotals
    meals: List[MealPlanItem] = Field(default_factory=list)
    total_prep_time_minutes: int


class MealPlanSummary(BaseModel):
    plan_id: UUID
    week_start_date: date
    week_end_date: date
    total: MealNutritionTotals
    daily: List[MealPlanDaySummary] = Field(default_factory=list)
    total_estimated_cost: float
    average_prep_time_minutes: float


class MealPlan(MealPlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    items: List[MealPlanItem] = Field(default_factory=list)

