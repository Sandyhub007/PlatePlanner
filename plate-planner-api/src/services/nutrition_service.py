"""
Nutrition Service
Handles nutrition calculation, aggregation, and goal tracking
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.database.models import User, MealPlan, MealPlanItem
from src.services.neo4j_service import Neo4jService
from src.utils.usda_client import get_usda_client, USDAClient
from src.utils.ingredient_matcher import normalize_ingredient_name

logger = logging.getLogger(__name__)


class NutritionService:
    """Service for nutrition calculations and tracking"""
    
    def __init__(self, db: Session, neo4j_service: Neo4jService):
        """
        Initialize Nutrition Service
        
        Args:
            db: SQLAlchemy database session
            neo4j_service: Neo4j service for recipe queries
        """
        self.db = db
        self.neo4j = neo4j_service
        self.usda_client = get_usda_client()
    
    def calculate_health_score(self, nutrition: Dict[str, float]) -> float:
        """
        Calculate health score for a recipe based on nutrition
        
        Algorithm:
            health_score = (fiber_score * 0.25 +
                          protein_score * 0.25 +
                          sodium_score * 0.20 +
                          sugar_score * 0.15 +
                          fat_quality_score * 0.15)
        
        Args:
            nutrition: Dict with nutrition values
        
        Returns:
            Health score (0-10, 10 = healthiest)
        """
        # Extract values
        fiber_g = nutrition.get("fiber_g", 0)
        protein_g = nutrition.get("protein_g", 0)
        sodium_mg = nutrition.get("sodium_mg", 0)
        sugar_g = nutrition.get("sugar_g", 0)
        fat_g = nutrition.get("fat_g", 0)
        saturated_fat_g = nutrition.get("saturated_fat_g", 0)
        
        # Fiber score (0-10)
        if fiber_g >= 12:
            fiber_score = 10
        elif fiber_g >= 8:
            fiber_score = 9
        elif fiber_g >= 5:
            fiber_score = 7
        elif fiber_g >= 3:
            fiber_score = 5
        else:
            fiber_score = 3
        
        # Protein score (0-10)
        if protein_g >= 40:
            protein_score = 10
        elif protein_g >= 30:
            protein_score = 9
        elif protein_g >= 20:
            protein_score = 7
        elif protein_g >= 10:
            protein_score = 5
        else:
            protein_score = 3
        
        # Sodium score (0-10) - lower is better
        if sodium_mg <= 400:
            sodium_score = 10
        elif sodium_mg <= 700:
            sodium_score = 8
        elif sodium_mg <= 1000:
            sodium_score = 6
        elif sodium_mg <= 1500:
            sodium_score = 4
        else:
            sodium_score = 2
        
        # Sugar score (0-10) - lower is better
        if sugar_g <= 5:
            sugar_score = 10
        elif sugar_g <= 10:
            sugar_score = 8
        elif sugar_g <= 15:
            sugar_score = 6
        elif sugar_g <= 25:
            sugar_score = 4
        else:
            sugar_score = 2
        
        # Fat quality score (based on saturated fat ratio)
        if fat_g > 0:
            saturated_ratio = saturated_fat_g / fat_g
            if saturated_ratio <= 0.1:
                fat_quality_score = 10
            elif saturated_ratio <= 0.2:
                fat_quality_score = 7
            elif saturated_ratio <= 0.3:
                fat_quality_score = 5
            else:
                fat_quality_score = 3
        else:
            fat_quality_score = 10  # No fat is good
        
        # Weighted average
        health_score = (
            fiber_score * 0.25 +
            protein_score * 0.25 +
            sodium_score * 0.20 +
            sugar_score * 0.15 +
            fat_quality_score * 0.15
        )
        
        return round(health_score, 1)
    
    async def get_ingredient_nutrition_from_cache_or_usda(
        self, 
        ingredient_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get ingredient nutrition from PostgreSQL cache or USDA API
        
        Args:
            ingredient_name: Name of ingredient
        
        Returns:
            Nutrition dictionary or None
        """
        # Normalize ingredient name
        normalized_name = normalize_ingredient_name(ingredient_name)
        
        # Try cache first
        from src.database.models import IngredientNutrition  # Avoid circular import
        
        cached = self.db.query(IngredientNutrition).filter(
            IngredientNutrition.normalized_name == normalized_name
        ).first()
        
        if cached:
            logger.debug(f"Cache hit for ingredient: {ingredient_name}")
            return {
                "ingredient_name": cached.ingredient_name,
                "calories": cached.calories,
                "protein_g": float(cached.protein_g),
                "carbs_g": float(cached.carbs_g),
                "fat_g": float(cached.fat_g),
                "fiber_g": float(cached.fiber_g) if cached.fiber_g else 0,
                "sugar_g": float(cached.sugar_g) if cached.sugar_g else 0,
                "sodium_mg": cached.sodium_mg or 0,
                "saturated_fat_g": float(cached.saturated_fat_g) if cached.saturated_fat_g else 0,
                "usda_fdc_id": cached.usda_fdc_id,
                "data_source": cached.data_source,
                "confidence_score": float(cached.confidence_score)
            }
        
        # Fetch from USDA
        logger.info(f"Fetching nutrition from USDA for: {ingredient_name}")
        async with self.usda_client as usda:
            nutrition = await usda.get_ingredient_nutrition(ingredient_name)
        
        if nutrition:
            # Cache it
            self._cache_ingredient_nutrition(ingredient_name, normalized_name, nutrition)
            return nutrition
        else:
            # Use fallback
            logger.warning(f"Using fallback nutrition for: {ingredient_name}")
            fallback = self.usda_client.get_fallback_nutrition(ingredient_name)
            self._cache_ingredient_nutrition(ingredient_name, normalized_name, fallback)
            return fallback
    
    def _cache_ingredient_nutrition(
        self, 
        ingredient_name: str, 
        normalized_name: str,
        nutrition: Dict[str, Any]
    ):
        """Save ingredient nutrition to cache"""
        from src.database.models import IngredientNutrition
        
        try:
            cached = IngredientNutrition(
                ingredient_name=ingredient_name,
                normalized_name=normalized_name,
                usda_fdc_id=nutrition.get("usda_fdc_id"),
                calories=nutrition["calories"],
                protein_g=nutrition["protein_g"],
                carbs_g=nutrition["carbs_g"],
                fat_g=nutrition["fat_g"],
                fiber_g=nutrition.get("fiber_g", 0),
                sugar_g=nutrition.get("sugar_g", 0),
                sodium_mg=nutrition.get("sodium_mg", 0),
                saturated_fat_g=nutrition.get("saturated_fat_g", 0),
                vitamin_a_mcg=nutrition.get("vitamin_a_mcg", 0),
                vitamin_c_mg=nutrition.get("vitamin_c_mg", 0),
                calcium_mg=nutrition.get("calcium_mg", 0),
                iron_mg=nutrition.get("iron_mg", 0),
                potassium_mg=nutrition.get("potassium_mg", 0),
                data_source=nutrition.get("data_source", "usda"),
                confidence_score=nutrition.get("confidence_score", 1.0)
            )
            self.db.add(cached)
            self.db.commit()
            logger.info(f"Cached nutrition for: {ingredient_name}")
        except Exception as e:
            logger.error(f"Error caching nutrition: {e}")
            self.db.rollback()
    
    async def calculate_recipe_nutrition(
        self, 
        recipe_id: str,
        servings: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate nutrition for a recipe
        
        Args:
            recipe_id: Neo4j recipe ID
            servings: Number of servings
        
        Returns:
            Nutrition dictionary with totals and per-serving values
        """
        # Get recipe ingredients from Neo4j
        query = """
        MATCH (r:Recipe {id: $recipe_id})-[rel:HAS_INGREDIENT]->(i:Ingredient)
        RETURN i.name as ingredient, 
               rel.quantity as quantity,
               rel.unit as unit,
               r.title as recipe_title,
               r.servings as recipe_servings
        """
        
        result = self.neo4j.execute_query(query, {"recipe_id": recipe_id})
        
        if not result:
            logger.warning(f"Recipe not found: {recipe_id}")
            return {}
        
        recipe_title = result[0]["recipe_title"]
        recipe_servings = result[0].get("recipe_servings", servings)
        
        # Initialize totals
        total_nutrition = {
            "calories": 0,
            "protein_g": 0.0,
            "carbs_g": 0.0,
            "fat_g": 0.0,
            "fiber_g": 0.0,
            "sugar_g": 0.0,
            "sodium_mg": 0,
            "saturated_fat_g": 0.0
        }
        
        ingredients_nutrition = []
        
        # Calculate for each ingredient
        for row in result:
            ingredient_name = row["ingredient"]
            quantity = row.get("quantity", 100)  # Default to 100g if not specified
            unit = row.get("unit", "g")
            
            # Get nutrition (per 100g from USDA)
            nutrition = await self.get_ingredient_nutrition_from_cache_or_usda(ingredient_name)
            
            if not nutrition:
                continue
            
            # Convert quantity to grams (simplified - you might want more sophisticated conversion)
            quantity_g = self._convert_to_grams(quantity, unit)
            
            # Scale nutrition to actual quantity
            scale_factor = quantity_g / 100.0
            
            ingredient_nutrition = {
                "ingredient": ingredient_name,
                "quantity": quantity,
                "unit": unit,
                "calories": int(nutrition["calories"] * scale_factor),
                "protein_g": round(nutrition["protein_g"] * scale_factor, 1),
                "carbs_g": round(nutrition["carbs_g"] * scale_factor, 1),
                "fat_g": round(nutrition["fat_g"] * scale_factor, 1),
                "data_quality": nutrition["data_source"]
            }
            
            ingredients_nutrition.append(ingredient_nutrition)
            
            # Add to totals
            total_nutrition["calories"] += ingredient_nutrition["calories"]
            total_nutrition["protein_g"] += ingredient_nutrition["protein_g"]
            total_nutrition["carbs_g"] += ingredient_nutrition["carbs_g"]
            total_nutrition["fat_g"] += ingredient_nutrition["fat_g"]
            total_nutrition["fiber_g"] += round(nutrition.get("fiber_g", 0) * scale_factor, 1)
            total_nutrition["sugar_g"] += round(nutrition.get("sugar_g", 0) * scale_factor, 1)
            total_nutrition["sodium_mg"] += int(nutrition.get("sodium_mg", 0) * scale_factor)
            total_nutrition["saturated_fat_g"] += round(nutrition.get("saturated_fat_g", 0) * scale_factor, 1)
        
        # Calculate per serving
        per_serving = {
            key: round(value / recipe_servings, 1) if isinstance(value, float) else int(value / recipe_servings)
            for key, value in total_nutrition.items()
        }
        
        # Calculate macro percentages (per serving)
        total_calories = per_serving["calories"]
        if total_calories > 0:
            protein_cal = per_serving["protein_g"] * 4
            carbs_cal = per_serving["carbs_g"] * 4
            fat_cal = per_serving["fat_g"] * 9
            total_macro_cal = protein_cal + carbs_cal + fat_cal
            
            if total_macro_cal > 0:
                macros_percentage = {
                    "protein_pct": int((protein_cal / total_macro_cal) * 100),
                    "carbs_pct": int((carbs_cal / total_macro_cal) * 100),
                    "fat_pct": int((fat_cal / total_macro_cal) * 100)
                }
            else:
                macros_percentage = {"protein_pct": 0, "carbs_pct": 0, "fat_pct": 0}
        else:
            macros_percentage = {"protein_pct": 0, "carbs_pct": 0, "fat_pct": 0}
        
        # Calculate health score
        health_score = self.calculate_health_score(per_serving)
        
        return {
            "recipe_id": recipe_id,
            "recipe_title": recipe_title,
            "servings": recipe_servings,
            "per_serving": per_serving,
            "total_recipe": total_nutrition,
            "macros_percentage": macros_percentage,
            "health_score": health_score,
            "ingredients_nutrition": ingredients_nutrition
        }
    
    def _convert_to_grams(self, quantity: float, unit: str) -> float:
        """
        Convert quantity to grams (simplified version)
        
        Args:
            quantity: Amount
            unit: Unit (g, kg, cup, tbsp, etc.)
        
        Returns:
            Quantity in grams
        """
        # Simplified conversion - in production, use pint or more comprehensive mapping
        conversions = {
            "g": 1.0,
            "gram": 1.0,
            "kg": 1000.0,
            "kilogram": 1000.0,
            "oz": 28.35,
            "ounce": 28.35,
            "lb": 453.59,
            "pound": 453.59,
            "cup": 240.0,  # Approximate for liquids
            "tbsp": 15.0,
            "tablespoon": 15.0,
            "tsp": 5.0,
            "teaspoon": 5.0,
            "ml": 1.0,  # Assuming 1ml ≈ 1g for water/liquids
            "liter": 1000.0,
            "item": 100.0,  # Default to 100g per item
            "piece": 100.0
        }
        
        unit_lower = unit.lower() if unit else "g"
        multiplier = conversions.get(unit_lower, 1.0)
        
        return quantity * multiplier
    
    async def aggregate_meal_plan_nutrition(
        self, 
        meal_plan_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Calculate total nutrition for entire meal plan
        
        Args:
            meal_plan_id: Meal plan UUID
            user_id: User UUID
        
        Returns:
            Aggregated nutrition with daily breakdown
        """
        # Get meal plan from database
        meal_plan = self.db.query(MealPlan).filter(
            and_(
                MealPlan.id == meal_plan_id,
                MealPlan.user_id == user_id
            )
        ).first()
        
        if not meal_plan:
            logger.warning(f"Meal plan not found: {meal_plan_id}")
            return {}

        # Day name mapping (0=Monday ... 6=Sunday)
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Initialize per-day accumulators
        daily_nutrition: Dict[int, Dict[str, Any]] = {}

        # Grand totals across entire plan
        grand_totals = {
            "calories": 0,
            "protein_g": 0.0,
            "carbs_g": 0.0,
            "fat_g": 0.0,
            "fiber_g": 0.0,
            "sugar_g": 0.0,
            "sodium_mg": 0,
            "saturated_fat_g": 0.0,
        }

        meal_details: List[Dict[str, Any]] = []
        health_scores: List[float] = []

        for item in meal_plan.items:
            day_key = item.day_of_week  # 0-6

            # Initialize day bucket if first time seeing this day
            if day_key not in daily_nutrition:
                daily_nutrition[day_key] = {
                    "date": (meal_plan.week_start_date + timedelta(days=day_key)).isoformat(),
                    "day_of_week": day_names[day_key] if 0 <= day_key <= 6 else f"Day {day_key}",
                    "calories": 0,
                    "protein_g": 0.0,
                    "carbs_g": 0.0,
                    "fat_g": 0.0,
                    "fiber_g": 0.0,
                    "sugar_g": 0.0,
                    "sodium_mg": 0,
                    "meals": [],
                }

            # Use stored per-item nutrition first (fast path, no API call needed)
            if item.calories is not None:
                meal_cal = item.calories
                meal_protein = float(item.protein or 0)
                meal_carbs = float(item.carbs or 0)
                meal_fat = float(item.fat or 0)
                meal_fiber = 0.0
                meal_sugar = 0.0
                meal_sodium = 0
                meal_health_score = self.calculate_health_score({
                    "fiber_g": meal_fiber,
                    "protein_g": meal_protein,
                    "sodium_mg": meal_sodium,
                    "sugar_g": meal_sugar,
                    "fat_g": meal_fat,
                    "saturated_fat_g": 0,
                })
            else:
                # Fall back to live calculation from Neo4j + USDA
                try:
                    recipe_nutrition = await self.calculate_recipe_nutrition(
                        item.recipe_id, item.servings or 1
                    )
                except Exception as exc:
                    logger.error(f"Failed to calculate nutrition for recipe {item.recipe_id}: {exc}")
                    recipe_nutrition = {}

                if not recipe_nutrition:
                    continue

                ps = recipe_nutrition.get("per_serving", {})
                meal_cal = ps.get("calories", 0)
                meal_protein = ps.get("protein_g", 0.0)
                meal_carbs = ps.get("carbs_g", 0.0)
                meal_fat = ps.get("fat_g", 0.0)
                meal_fiber = ps.get("fiber_g", 0.0)
                meal_sugar = ps.get("sugar_g", 0.0)
                meal_sodium = ps.get("sodium_mg", 0)
                meal_health_score = recipe_nutrition.get("health_score", 5.0)

            health_scores.append(meal_health_score)

            # Accumulate into daily bucket
            daily_nutrition[day_key]["calories"] += meal_cal
            daily_nutrition[day_key]["protein_g"] += meal_protein
            daily_nutrition[day_key]["carbs_g"] += meal_carbs
            daily_nutrition[day_key]["fat_g"] += meal_fat
            daily_nutrition[day_key]["fiber_g"] += meal_fiber
            daily_nutrition[day_key]["sugar_g"] += meal_sugar
            daily_nutrition[day_key]["sodium_mg"] += meal_sodium
            daily_nutrition[day_key]["meals"].append({
                "meal_type": item.meal_type,
                "recipe_id": item.recipe_id,
                "recipe_title": item.recipe_title,
                "servings": item.servings or 1,
                "calories": meal_cal,
                "protein_g": round(meal_protein, 1),
                "carbs_g": round(meal_carbs, 1),
                "fat_g": round(meal_fat, 1),
                "health_score": round(meal_health_score, 1),
            })

            # Accumulate grand totals
            grand_totals["calories"] += meal_cal
            grand_totals["protein_g"] += meal_protein
            grand_totals["carbs_g"] += meal_carbs
            grand_totals["fat_g"] += meal_fat
            grand_totals["fiber_g"] += meal_fiber
            grand_totals["sugar_g"] += meal_sugar
            grand_totals["sodium_mg"] += meal_sodium

        # Round grand totals
        for key in ["protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g"]:
            grand_totals[key] = round(grand_totals[key], 1)

        # Build sorted daily breakdown
        num_days = len(daily_nutrition) or 1
        daily_breakdown = []
        for day_num in sorted(daily_nutrition.keys()):
            day = daily_nutrition[day_num]
            # Round float fields
            for fk in ["protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g"]:
                day[fk] = round(day[fk], 1)
            daily_breakdown.append(day)

        # Daily averages
        daily_averages = {
            "calories": int(grand_totals["calories"] / num_days),
            "protein_g": round(grand_totals["protein_g"] / num_days, 1),
            "carbs_g": round(grand_totals["carbs_g"] / num_days, 1),
            "fat_g": round(grand_totals["fat_g"] / num_days, 1),
            "fiber_g": round(grand_totals["fiber_g"] / num_days, 1),
            "sugar_g": round(grand_totals["sugar_g"] / num_days, 1),
            "sodium_mg": int(grand_totals["sodium_mg"] / num_days),
        }

        # Average health score
        avg_health_score = round(sum(health_scores) / len(health_scores), 1) if health_scores else 5.0

        return {
            "plan_id": meal_plan_id,
            "week_start": meal_plan.week_start_date.isoformat(),
            "week_end": meal_plan.week_end_date.isoformat(),
            "total_nutrition": grand_totals,
            "daily_averages": daily_averages,
            "daily_breakdown": daily_breakdown,
            "avg_health_score": avg_health_score,
            "total_meals": len(meal_plan.items),
            "days_with_meals": num_days,
        }


def get_nutrition_service(db: Session, neo4j_service: Neo4jService) -> NutritionService:
    """Factory function to get nutrition service"""
    return NutritionService(db, neo4j_service)

