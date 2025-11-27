import uuid
from sqlalchemy import Boolean, Column, String, Integer, Float, ForeignKey, DateTime, ARRAY, Text, Date, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    meal_plans = relationship("MealPlan", back_populates="user", cascade="all, delete-orphan")
    shopping_lists = relationship("ShoppingList", back_populates="user", cascade="all, delete-orphan")

class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Dietary Preferences
    dietary_restrictions = Column(ARRAY(String), default=[])  # e.g., ["vegan", "gluten-free"]
    allergies = Column(ARRAY(String), default=[])
    cuisine_preferences = Column(ARRAY(String), default=[])
    
    # Nutrition Targets
    calorie_target = Column(Integer, nullable=True)
    protein_target = Column(Integer, nullable=True)
    carb_target = Column(Integer, nullable=True)
    fat_target = Column(Integer, nullable=True)
    
    # Other Constraints
    cooking_time_max = Column(Integer, nullable=True)  # minutes
    budget_per_week = Column(Float, nullable=True)
    people_count = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="preferences")

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    status = Column(String, default="draft")  # draft, active, completed
    total_calories = Column(Integer, default=0)
    total_protein = Column(Integer, default=0)
    total_carbs = Column(Integer, default=0)
    total_fat = Column(Integer, default=0)
    total_estimated_cost = Column(Float, default=0.0)
    is_valid = Column(Boolean, default=True)
    validation_issues = Column(JSON, default=list)
    last_validated_at = Column(DateTime, nullable=True)
    summary_snapshot = Column(JSON, default=dict)
    summary_generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="meal_plans")
    items = relationship("MealPlanItem", back_populates="meal_plan", cascade="all, delete-orphan")
    shopping_lists = relationship("ShoppingList", back_populates="meal_plan", cascade="all, delete-orphan")

class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("meal_plans.id"), nullable=False)
    
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    meal_type = Column(String, nullable=False)     # breakfast, lunch, dinner
    
    recipe_id = Column(String, nullable=False)     # References Neo4j ID
    recipe_title = Column(String, nullable=False)
    servings = Column(Integer, default=1)
    calories = Column(Integer, nullable=True)
    protein = Column(Integer, nullable=True)
    carbs = Column(Integer, nullable=True)
    fat = Column(Integer, nullable=True)
    estimated_cost = Column(Float, default=0.0)
    prep_time_minutes = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    meal_plan = relationship("MealPlan", back_populates="items")


# ===== Phase 3: Shopping List Models =====

class ShoppingList(Base):
    """Shopping list generated from meal plans or created manually."""
    __tablename__ = "shopping_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("meal_plans.id"), nullable=True, index=True)
    
    name = Column(String(255), default="Shopping List")
    status = Column(String(50), default="active", index=True)  # active, completed, archived
    
    total_estimated_cost = Column(Float, default=0.0)
    total_items = Column(Integer, default=0)
    purchased_items = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="shopping_lists")
    meal_plan = relationship("MealPlan", back_populates="shopping_lists")
    items = relationship("ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingListItem(Base):
    """Individual item in a shopping list."""
    __tablename__ = "shopping_list_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    list_id = Column(UUID(as_uuid=True), ForeignKey("shopping_lists.id"), nullable=False, index=True)
    
    ingredient_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), index=True)  # for fuzzy matching
    
    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    
    category = Column(String(100), default="Other", index=True)
    
    estimated_price = Column(Float, nullable=True)
    store_prices = Column(JSON, nullable=True)  # {"walmart": 3.99, "kroger": 4.29}
    
    is_purchased = Column(Boolean, default=False, index=True)
    is_manual = Column(Boolean, default=False)  # user-added vs auto-generated
    
    recipe_references = Column(ARRAY(String), default=[])  # array of recipe titles
    
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    shopping_list = relationship("ShoppingList", back_populates="items")
