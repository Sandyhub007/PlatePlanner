"""
Pydantic schemas for nutrition and dietary profiles
"""
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field, validator
from enum import Enum


# ========================================
# Enums
# ========================================

class DietaryRestriction(str, Enum):
    """Supported dietary restrictions"""
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    PESCATARIAN = "pescatarian"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    LOW_FAT = "low_fat"
    HIGH_PROTEIN = "high_protein"
    HALAL = "halal"
    KOSHER = "kosher"


class Allergen(str, Enum):
    """Common allergens"""
    NUTS = "nuts"
    PEANUTS = "peanuts"
    TREE_NUTS = "tree_nuts"
    DAIRY = "dairy"
    EGGS = "eggs"
    GLUTEN = "gluten"
    WHEAT = "wheat"
    SOY = "soy"
    FISH = "fish"
    SHELLFISH = "shellfish"
    SESAME = "sesame"


class GoalType(str, Enum):
    """Nutrition goal types"""
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    MAINTENANCE = "maintenance"
    GENERAL_HEALTH = "general_health"
    ATHLETIC_PERFORMANCE = "athletic_performance"


# ========================================
# Dietary Profile Schemas
# ========================================

class DietaryProfileBase(BaseModel):
    """Base dietary profile"""
    dietary_restrictions: List[DietaryRestriction] = Field(default_factory=list)
    allergens: List[Allergen] = Field(default_factory=list)
    
    # Nutrition targets (daily)
    calorie_target: Optional[int] = Field(None, ge=1000, le=5000)
    protein_target_g: Optional[int] = Field(None, ge=0, le=500)
    carbs_target_g: Optional[int] = Field(None, ge=0, le=1000)
    fat_target_g: Optional[int] = Field(None, ge=0, le=300)
    
    health_goal: Optional[GoalType] = None


class DietaryProfileCreate(DietaryProfileBase):
    """Create dietary profile"""
    pass


class DietaryProfileUpdate(BaseModel):
    """Update dietary profile (all fields optional)"""
    dietary_restrictions: Optional[List[DietaryRestriction]] = None
    allergens: Optional[List[Allergen]] = None
    calorie_target: Optional[int] = Field(None, ge=1000, le=5000)
    protein_target_g: Optional[int] = Field(None, ge=0, le=500)
    carbs_target_g: Optional[int] = Field(None, ge=0, le=1000)
    fat_target_g: Optional[int] = Field(None, ge=0, le=300)
    health_goal: Optional[GoalType] = None


class DietaryProfile(DietaryProfileBase):
    """Dietary profile response"""
    user_id: str
    
    class Config:
        from_attributes = True


# ========================================
# Nutrition Info Schemas
# ========================================

class NutritionMacros(BaseModel):
    """Macronutrient information"""
    calories: int = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    carbs_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    fiber_g: float = Field(0, ge=0)
    sugar_g: float = Field(0, ge=0)
    sodium_mg: int = Field(0, ge=0)


class NutritionDetailed(NutritionMacros):
    """Detailed nutrition information"""
    saturated_fat_g: float = Field(0, ge=0)
    trans_fat_g: float = Field(0, ge=0)
    vitamin_a_mcg: int = Field(0, ge=0)
    vitamin_c_mg: int = Field(0, ge=0)
    calcium_mg: int = Field(0, ge=0)
    iron_mg: float = Field(0, ge=0)
    potassium_mg: int = Field(0, ge=0)


class MacroPercentages(BaseModel):
    """Macronutrient percentages"""
    protein_pct: int = Field(..., ge=0, le=100)
    carbs_pct: int = Field(..., ge=0, le=100)
    fat_pct: int = Field(..., ge=0, le=100)
    
    @validator('fat_pct')
    def validate_total(cls, v, values):
        """Ensure percentages sum to ~100%"""
        total = values.get('protein_pct', 0) + values.get('carbs_pct', 0) + v
        if not (95 <= total <= 105):  # Allow 5% tolerance
            raise ValueError(f"Macro percentages must sum to ~100% (got {total}%)")
        return v


# ========================================
# Recipe Nutrition Schemas
# ========================================

class RecipeDietaryInfo(BaseModel):
    """Recipe dietary classifications"""
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_pescatarian: bool = False
    is_gluten_free: bool = False
    is_dairy_free: bool = False
    is_keto_friendly: bool = False
    is_paleo: bool = False
    is_low_carb: bool = False
    is_high_protein: bool = False
    allergens: List[Allergen] = Field(default_factory=list)


class HealthFactors(BaseModel):
    """Health indicators for a recipe"""
    high_protein: bool = False
    high_fiber: bool = False
    low_sodium: bool = False
    low_sugar: bool = False
    low_fat: bool = False
    healthy_fats: bool = False


class IngredientNutrition(BaseModel):
    """Nutrition for a single ingredient"""
    ingredient: str
    quantity: float
    unit: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    data_quality: str = "usda"  # 'usda', 'estimated', 'manual'


class RecipeNutrition(BaseModel):
    """Complete recipe nutrition information"""
    recipe_id: str
    recipe_title: str
    servings: int
    
    per_serving: NutritionMacros
    total_recipe: NutritionMacros
    macros_percentage: MacroPercentages
    
    health_score: float = Field(..., ge=0, le=10)
    health_factors: HealthFactors
    dietary_info: RecipeDietaryInfo
    
    ingredients_nutrition: List[IngredientNutrition] = Field(default_factory=list)


# ========================================
# Nutrition Goals Schemas
# ========================================

class NutritionGoalBase(BaseModel):
    """Base nutrition goal"""
    goal_type: GoalType
    daily_calorie_target: int = Field(..., ge=1000, le=5000)
    daily_protein_g_target: Optional[int] = Field(None, ge=0, le=500)
    daily_carbs_g_target: Optional[int] = Field(None, ge=0, le=1000)
    daily_fat_g_target: Optional[int] = Field(None, ge=0, le=300)
    start_date: date
    duration_days: Optional[int] = Field(None, ge=1, le=365)


class NutritionGoalCreate(NutritionGoalBase):
    """Create nutrition goal"""
    pass


class NutritionGoal(NutritionGoalBase):
    """Nutrition goal response"""
    id: str
    user_id: str
    end_date: Optional[date] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class MacroTargets(BaseModel):
    """Daily macro targets"""
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int


class GoalProgress(BaseModel):
    """Goal achievement progress"""
    has_active_goal: bool
    goal_type: Optional[GoalType] = None
    calorie_target: Optional[int] = None
    calorie_actual_avg: Optional[int] = None
    achievement_pct: Optional[float] = None
    status: Optional[str] = None  # 'on_track', 'over', 'under'
    days_on_track: Optional[int] = None
    days_off_track: Optional[int] = None


# ========================================
# Meal Plan Nutrition Schemas
# ========================================

class MealNutrition(BaseModel):
    """Nutrition for a single meal"""
    meal_type: str  # breakfast, lunch, dinner, snack
    recipe_id: str
    recipe_title: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    health_score: float


class DayNutrition(BaseModel):
    """Nutrition for a single day"""
    date: date
    day_of_week: str
    meals: List[MealNutrition]
    daily_total: NutritionMacros


class MealPlanNutrition(BaseModel):
    """Complete meal plan nutrition"""
    plan_id: str
    week_start: date
    week_end: date
    
    total_nutrition: NutritionMacros
    daily_average: NutritionMacros
    
    breakdown_by_day: List[DayNutrition]
    
    goal_comparison: GoalProgress
    health_insights: List[str] = Field(default_factory=list)


# ========================================
# Nutrition Summary Schemas
# ========================================

class NutritionPeriod(BaseModel):
    """Time period for summary"""
    start_date: date
    end_date: date
    days: int


class HealthMetrics(BaseModel):
    """Aggregated health metrics"""
    avg_health_score: float = Field(..., ge=0, le=10)
    high_protein_meals: int = Field(0, ge=0)
    low_sodium_meals: int = Field(0, ge=0)
    high_fiber_meals: int = Field(0, ge=0)


class NutritionRecommendation(BaseModel):
    """Personalized recommendation"""
    type: str
    message: str
    recipe_suggestions: List[str] = Field(default_factory=list)


class NutritionSummary(BaseModel):
    """Weekly/monthly nutrition summary"""
    user_id: str
    period: NutritionPeriod
    
    totals: NutritionMacros
    daily_averages: NutritionMacros
    macro_distribution: MacroPercentages
    
    goal_progress: GoalProgress
    health_metrics: HealthMetrics
    
    insights: List[str] = Field(default_factory=list)
    recommendations: List[NutritionRecommendation] = Field(default_factory=list)


# ========================================
# Healthy Alternatives Schema
# ========================================

class HealthyAlternative(BaseModel):
    """Healthier recipe alternative"""
    original_recipe_id: str
    original_recipe_title: str
    original_health_score: float
    
    alternative_recipe_id: str
    alternative_recipe_title: str
    alternative_health_score: float
    
    improvement_pct: float
    reason: str
    
    nutrition_comparison: dict  # {metric: {original: val, alternative: val}}

