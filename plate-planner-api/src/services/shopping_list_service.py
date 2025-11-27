"""Shopping List Service - Phase 3

This service handles:
1. Extracting ingredients from meal plans
2. Consolidating duplicate ingredients
3. Categorizing ingredients
4. Managing shopping lists
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from src.config.paths import DataPaths
from src.database import models
from src.schemas.shopping_list import (
    ShoppingListGenerateRequest,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
)
from src.utils.ingredient_matcher import (
    group_similar_ingredients,
    normalize_ingredient_name as _normalize_ingredient_name,
)
from src.utils.unit_converter import (
    consolidate_quantities,
    normalize_unit,
)


# ===== Helper Functions =====

# Note: _normalize_ingredient_name is now imported from ingredient_matcher


def _load_recipe_ingredients_from_neo4j(recipe_id: str) -> List[str]:
    """
    Load ingredient list for a recipe from Neo4j.
    
    Tries Neo4j first, falls back to CSV if Neo4j is unavailable.
    """
    # Try Neo4j first
    try:
        from src.services.neo4j_service import get_recipe_ingredients_by_id
        ingredients = get_recipe_ingredients_by_id(recipe_id)
        if ingredients:
            return ingredients
    except Exception:
        # Fallback to CSV if Neo4j fails
        pass
    
    # Fallback: Read from CSV
    paths = DataPaths()
    ingredients = []
    try:
        with open(paths.recipe_ingredients, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('recipe_id') == str(recipe_id):
                    ingredient_name = row.get('ingredient', '').strip()
                    if ingredient_name:
                        ingredients.append(ingredient_name)
    except FileNotFoundError:
        # Return empty list if CSV not found
        pass
    
    return ingredients


def _extract_ingredients_from_meal_plan(
    db: Session,
    plan: models.MealPlan
) -> List[Dict]:
    """
    Extract all ingredients from meal plan recipes with advanced consolidation.
    
    Uses fuzzy matching to group similar ingredients and unit conversion
    to consolidate quantities.
    
    Returns list of dicts with:
    - ingredient_name: str
    - quantity: float (consolidated)
    - unit: str (normalized)
    - recipe_references: List[str]
    """
    # Step 1: Extract all ingredients with quantities
    raw_ingredients: List[Dict] = []
    
    for item in plan.items:
        # Load ingredients for this recipe
        recipe_ingredients = _load_recipe_ingredients_from_neo4j(item.recipe_id)
        
        for ing_name in recipe_ingredients:
            # For now, use placeholder quantity/unit
            # In future, parse from recipe data
            raw_ingredients.append({
                "ingredient_name": ing_name,
                "quantity": float(item.servings),  # Scale by servings
                "unit": "item",  # Placeholder - will be improved in future
                "recipe_references": [item.recipe_title],
            })
    
    # Step 2: Group similar ingredients using fuzzy matching
    grouped = group_similar_ingredients(raw_ingredients, threshold=85)
    
    # Step 3: Consolidate quantities with unit conversion
    consolidated: List[Dict] = []
    for group in grouped:
        # Consolidate quantities (convert units if possible)
        total_qty, best_unit = consolidate_quantities(group["quantities"])
        
        consolidated.append({
            "ingredient_name": group["ingredient_name"],
            "normalized_name": normalize_ingredient_name(group["ingredient_name"]),
            "quantity": total_qty,
            "unit": normalize_unit(best_unit),
            "recipe_references": group["recipe_references"],
        })
    
    return consolidated


def _classify_ingredient_category(ingredient_name: str) -> str:
    """
    Classify ingredient into category using keyword matching.
    
    Categories:
    - Produce
    - Meat & Seafood
    - Dairy & Eggs
    - Bakery & Bread
    - Pantry
    - Frozen Foods
    - Beverages
    - Spices & Condiments
    - Other (default)
    
    This is a basic implementation. Week 2 will add ML-based classification.
    """
    name_lower = ingredient_name.lower()
    
    # Produce
    produce_keywords = {
        'tomato', 'lettuce', 'onion', 'garlic', 'potato', 'carrot',
        'celery', 'pepper', 'cucumber', 'spinach', 'broccoli', 'cauliflower',
        'cabbage', 'mushroom', 'zucchini', 'squash', 'eggplant', 'avocado',
        'apple', 'banana', 'orange', 'lemon', 'lime', 'strawberry', 'berry',
        'grape', 'melon', 'pineapple', 'mango', 'peach', 'pear', 'plum',
        'vegetable', 'fruit', 'salad', 'herb', 'cilantro', 'parsley', 'basil',
        'thyme', 'rosemary', 'mint', 'kale', 'arugula', 'chard'
    }
    
    # Meat & Seafood
    meat_keywords = {
        'chicken', 'beef', 'pork', 'turkey', 'lamb', 'duck', 'ham',
        'bacon', 'sausage', 'steak', 'ground', 'breast', 'thigh', 'wing',
        'fish', 'salmon', 'tuna', 'cod', 'tilapia', 'shrimp', 'prawn',
        'lobster', 'crab', 'scallop', 'clam', 'mussel', 'oyster', 'seafood',
        'meat', 'veal', 'ribs', 'chop', 'roast'
    }
    
    # Dairy & Eggs
    dairy_keywords = {
        'milk', 'cream', 'butter', 'cheese', 'yogurt', 'sour cream',
        'cottage cheese', 'ricotta', 'mozzarella', 'cheddar', 'parmesan',
        'feta', 'goat cheese', 'cream cheese', 'egg', 'eggs', 'dairy',
        'ice cream', 'whipped cream', 'half and half', 'buttermilk'
    }
    
    # Bakery & Bread
    bakery_keywords = {
        'bread', 'baguette', 'roll', 'bun', 'bagel', 'croissant',
        'tortilla', 'pita', 'naan', 'flatbread', 'muffin', 'donut',
        'pastry', 'cake', 'pie', 'cookie', 'biscuit'
    }
    
    # Pantry
    pantry_keywords = {
        'flour', 'sugar', 'salt', 'rice', 'pasta', 'noodle', 'grain',
        'oat', 'cereal', 'beans', 'lentil', 'chickpea', 'kidney bean',
        'black bean', 'pinto bean', 'quinoa', 'barley', 'couscous',
        'oil', 'olive oil', 'vegetable oil', 'canola oil', 'sesame oil',
        'vinegar', 'balsamic', 'soy sauce', 'worcestershire', 'ketchup',
        'mustard', 'mayonnaise', 'mayo', 'hot sauce', 'salsa',
        'tomato sauce', 'pasta sauce', 'marinara', 'broth', 'stock',
        'bouillon', 'soup', 'canned', 'jar', 'bottle'
    }
    
    # Frozen Foods
    frozen_keywords = {
        'frozen', 'ice', 'popsicle', 'sherbet', 'sorbet'
    }
    
    # Beverages
    beverage_keywords = {
        'water', 'juice', 'soda', 'pop', 'cola', 'lemonade', 'tea',
        'coffee', 'wine', 'beer', 'liquor', 'vodka', 'rum', 'whiskey',
        'bourbon', 'gin', 'tequila', 'cocktail', 'drink', 'beverage'
    }
    
    # Spices & Condiments
    spice_keywords = {
        'pepper', 'paprika', 'cumin', 'coriander', 'turmeric', 'curry',
        'chili', 'cayenne', 'cinnamon', 'nutmeg', 'ginger', 'clove',
        'cardamom', 'fennel', 'oregano', 'sage', 'dill', 'bay leaf',
        'vanilla', 'extract', 'spice', 'seasoning', 'blend', 'powder'
    }
    
    # Check keywords in order
    for keyword in produce_keywords:
        if keyword in name_lower:
            return "Produce"
    
    for keyword in meat_keywords:
        if keyword in name_lower:
            return "Meat & Seafood"
    
    for keyword in dairy_keywords:
        if keyword in name_lower:
            return "Dairy & Eggs"
    
    for keyword in bakery_keywords:
        if keyword in name_lower:
            return "Bakery & Bread"
    
    for keyword in frozen_keywords:
        if keyword in name_lower:
            return "Frozen Foods"
    
    for keyword in beverage_keywords:
        if keyword in name_lower:
            return "Beverages"
    
    for keyword in spice_keywords:
        if keyword in name_lower:
            return "Spices & Condiments"
    
    for keyword in pantry_keywords:
        if keyword in name_lower:
            return "Pantry"
    
    return "Other"


def _estimate_ingredient_price(
    ingredient_name: str,
    quantity: float,
    unit: str,
    category: str
) -> float:
    """
    Estimate price for an ingredient.
    
    This is a simple heuristic for Week 1.
    Week 4 will implement proper price estimation.
    """
    # Basic price ranges by category (per unit)
    category_base_prices = {
        "Produce": 2.0,
        "Meat & Seafood": 8.0,
        "Dairy & Eggs": 4.0,
        "Bakery & Bread": 3.0,
        "Pantry": 3.0,
        "Frozen Foods": 4.0,
        "Beverages": 3.0,
        "Spices & Condiments": 5.0,
        "Other": 3.0,
    }
    
    base_price = category_base_prices.get(category, 3.0)
    
    # Simple quantity multiplier
    estimated = base_price * max(quantity, 1.0) * 0.5  # Scale down a bit
    
    return round(estimated, 2)


# ===== Main Service Functions =====

def generate_shopping_list(
    db: Session,
    user_id: UUID,
    request: ShoppingListGenerateRequest
) -> models.ShoppingList:
    """
    Generate a shopping list from a meal plan.
    
    Args:
        db: Database session
        user_id: User ID
        request: Shopping list generation request
    
    Returns:
        Generated shopping list with items
    """
    # Load meal plan with items
    meal_plan = (
        db.query(models.MealPlan)
        .options(selectinload(models.MealPlan.items))
        .filter(
            models.MealPlan.id == request.plan_id,
            models.MealPlan.user_id == user_id
        )
        .first()
    )
    
    if not meal_plan:
        raise ValueError("Meal plan not found or not accessible")
    
    # Extract ingredients from recipes
    ingredients = _extract_ingredients_from_meal_plan(db, meal_plan)
    
    # Filter out excluded items
    if request.exclude_items:
        exclude_normalized = {_normalize_ingredient_name(item) for item in request.exclude_items}
        ingredients = [
            ing for ing in ingredients
            if ing["normalized_name"] not in exclude_normalized
        ]
    
    # Create shopping list
    shopping_list = models.ShoppingList(
        user_id=user_id,
        plan_id=request.plan_id,
        name=request.name or f"Shopping List - {meal_plan.week_start_date.strftime('%b %d')}",
        status="active",
        total_items=len(ingredients),
        purchased_items=0,
    )
    db.add(shopping_list)
    db.flush()  # Get shopping_list.id
    
    # Create shopping list items
    total_cost = 0.0
    for ing_data in ingredients:
        category = _classify_ingredient_category(ing_data["ingredient_name"])
        estimated_price = _estimate_ingredient_price(
            ing_data["ingredient_name"],
            ing_data["quantity"],
            ing_data["unit"],
            category
        )
        total_cost += estimated_price
        
        item = models.ShoppingListItem(
            list_id=shopping_list.id,
            ingredient_name=ing_data["ingredient_name"],
            normalized_name=ing_data["normalized_name"],
            quantity=ing_data["quantity"],
            unit=ing_data["unit"],
            category=category,
            estimated_price=estimated_price,
            is_purchased=False,
            is_manual=False,
            recipe_references=ing_data["recipe_references"],
        )
        db.add(item)
    
    shopping_list.total_estimated_cost = round(total_cost, 2)
    db.add(shopping_list)
    db.commit()
    db.refresh(shopping_list)
    
    return shopping_list


def get_shopping_list(
    db: Session,
    user_id: UUID,
    list_id: UUID
) -> Optional[models.ShoppingList]:
    """Get a shopping list by ID"""
    return (
        db.query(models.ShoppingList)
        .options(selectinload(models.ShoppingList.items))
        .filter(
            models.ShoppingList.id == list_id,
            models.ShoppingList.user_id == user_id
        )
        .first()
    )


def get_user_shopping_lists(
    db: Session,
    user_id: UUID,
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> Tuple[List[models.ShoppingList], int]:
    """
    Get all shopping lists for a user.
    
    Returns:
        Tuple of (lists, total_count)
    """
    query = db.query(models.ShoppingList).filter(
        models.ShoppingList.user_id == user_id
    )
    
    if status:
        query = query.filter(models.ShoppingList.status == status)
    
    total = query.count()
    
    lists = (
        query
        .order_by(models.ShoppingList.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    return lists, total


def add_manual_item(
    db: Session,
    user_id: UUID,
    list_id: UUID,
    item_data: ShoppingListItemCreate
) -> models.ShoppingListItem:
    """Add a manual item to shopping list"""
    # Verify list belongs to user
    shopping_list = get_shopping_list(db, user_id, list_id)
    if not shopping_list:
        raise ValueError("Shopping list not found or not accessible")
    
    # Classify category
    category = item_data.category or _classify_ingredient_category(item_data.ingredient_name)
    
    # Estimate price
    estimated_price = _estimate_ingredient_price(
        item_data.ingredient_name,
        item_data.quantity or 1.0,
        item_data.unit or "item",
        category
    )
    
    # Create item
    item = models.ShoppingListItem(
        list_id=list_id,
        ingredient_name=item_data.ingredient_name,
        normalized_name=_normalize_ingredient_name(item_data.ingredient_name),
        quantity=item_data.quantity,
        unit=item_data.unit,
        category=category,
        estimated_price=estimated_price,
        is_purchased=False,
        is_manual=True,
        notes=item_data.notes,
    )
    db.add(item)
    
    # Update list totals
    shopping_list.total_items += 1
    shopping_list.total_estimated_cost += estimated_price
    shopping_list.updated_at = datetime.utcnow()
    db.add(shopping_list)
    
    db.commit()
    db.refresh(item)
    
    return item


def update_shopping_list_item(
    db: Session,
    user_id: UUID,
    list_id: UUID,
    item_id: UUID,
    updates: ShoppingListItemUpdate
) -> models.ShoppingListItem:
    """Update a shopping list item"""
    # Verify list belongs to user
    shopping_list = get_shopping_list(db, user_id, list_id)
    if not shopping_list:
        raise ValueError("Shopping list not found or not accessible")
    
    # Find item
    item = next((i for i in shopping_list.items if i.id == item_id), None)
    if not item:
        raise ValueError("Item not found in shopping list")
    
    # Track purchase status change
    was_purchased = item.is_purchased
    
    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    
    item.updated_at = datetime.utcnow()
    db.add(item)
    
    # Update list purchased count
    if updates.is_purchased is not None and updates.is_purchased != was_purchased:
        if updates.is_purchased:
            shopping_list.purchased_items += 1
        else:
            shopping_list.purchased_items -= 1
        shopping_list.updated_at = datetime.utcnow()
        db.add(shopping_list)
    
    db.commit()
    db.refresh(item)
    
    return item


def delete_shopping_list_item(
    db: Session,
    user_id: UUID,
    list_id: UUID,
    item_id: UUID
) -> None:
    """Delete a shopping list item"""
    # Verify list belongs to user
    shopping_list = get_shopping_list(db, user_id, list_id)
    if not shopping_list:
        raise ValueError("Shopping list not found or not accessible")
    
    # Find and delete item
    item = next((i for i in shopping_list.items if i.id == item_id), None)
    if not item:
        raise ValueError("Item not found in shopping list")
    
    # Update list totals
    shopping_list.total_items -= 1
    if item.is_purchased:
        shopping_list.purchased_items -= 1
    shopping_list.total_estimated_cost -= (item.estimated_price or 0.0)
    shopping_list.updated_at = datetime.utcnow()
    
    db.delete(item)
    db.add(shopping_list)
    db.commit()


def complete_shopping_list(
    db: Session,
    user_id: UUID,
    list_id: UUID
) -> models.ShoppingList:
    """Mark all items as purchased and complete the list"""
    shopping_list = get_shopping_list(db, user_id, list_id)
    if not shopping_list:
        raise ValueError("Shopping list not found or not accessible")
    
    # Mark all items as purchased
    for item in shopping_list.items:
        if not item.is_purchased:
            item.is_purchased = True
            db.add(item)
    
    # Update list status
    shopping_list.status = "completed"
    shopping_list.purchased_items = shopping_list.total_items
    shopping_list.completed_at = datetime.utcnow()
    shopping_list.updated_at = datetime.utcnow()
    db.add(shopping_list)
    
    db.commit()
    db.refresh(shopping_list)
    
    return shopping_list


def delete_shopping_list(
    db: Session,
    user_id: UUID,
    list_id: UUID
) -> None:
    """Delete a shopping list"""
    shopping_list = get_shopping_list(db, user_id, list_id)
    if not shopping_list:
        raise ValueError("Shopping list not found or not accessible")
    
    db.delete(shopping_list)
    db.commit()

