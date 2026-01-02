"""
Healthy Alternatives Service
Finds healthier recipe alternatives based on health scores
"""
import logging
from typing import List, Optional, Dict
from src.services.neo4j_service import Neo4jService
from src.schemas.nutrition import HealthyAlternative, DietaryRestriction, Allergen

logger = logging.getLogger(__name__)


class HealthyAlternativesService:
    """
    Service for finding healthier alternatives to recipes
    """
    
    def __init__(self, neo4j_service: Neo4jService):
        """
        Initialize healthy alternatives service
        
        Args:
            neo4j_service: Neo4j service for querying recipes
        """
        self.neo4j = neo4j_service
    
    def find_healthier_alternative(
        self,
        recipe_id: str,
        dietary_restrictions: Optional[List[DietaryRestriction]] = None,
        allergens: Optional[List[Allergen]] = None,
        min_score_improvement: float = 0.5
    ) -> Optional[HealthyAlternative]:
        """
        Find a healthier alternative to a recipe
        
        Args:
            recipe_id: Original recipe ID
            dietary_restrictions: User's dietary restrictions
            allergens: User's allergens to avoid
            min_score_improvement: Minimum health score improvement required
        
        Returns:
            HealthyAlternative or None if no suitable alternative found
        """
        # Get original recipe
        query = """
        MATCH (r:Recipe {id: $recipe_id})
        RETURN r.id as id,
               r.title as title,
               r.health_score as health_score,
               r.calories_per_serving as calories,
               r.protein_g as protein_g,
               r.carbs_g as carbs_g,
               r.fat_g as fat_g,
               r.sodium_mg as sodium_mg
        """
        
        original = self.neo4j.execute_query(query, {"recipe_id": recipe_id})
        
        if not original:
            logger.warning(f"Recipe not found: {recipe_id}")
            return None
        
        original = original[0]
        original_score = original.get("health_score") or 5.0
        
        # Build dietary filter
        dietary_filter = self._build_dietary_filter(dietary_restrictions, allergens)
        
        # Find similar but healthier recipes
        query = f"""
        MATCH (r1:Recipe {{id: $recipe_id}})-[:HAS_INGREDIENT]->(i:Ingredient)<-[:HAS_INGREDIENT]-(r2:Recipe)
        WHERE r2.id <> $recipe_id
          AND r2.health_score IS NOT NULL
          AND r2.health_score > $min_score
          {dietary_filter}
        WITH r2, count(i) as common_ingredients,
             r2.health_score as alt_score
        ORDER BY alt_score DESC, common_ingredients DESC
        LIMIT 5
        RETURN r2.id as id,
               r2.title as title,
               r2.health_score as health_score,
               r2.calories_per_serving as calories,
               r2.protein_g as protein_g,
               r2.carbs_g as carbs_g,
               r2.fat_g as fat_g,
               r2.sodium_mg as sodium_mg,
               common_ingredients
        """
        
        params = {
            "recipe_id": recipe_id,
            "min_score": original_score + min_score_improvement
        }
        
        alternatives = self.neo4j.execute_query(query, params)
        
        if not alternatives:
            logger.info(f"No healthier alternatives found for recipe {recipe_id}")
            return None
        
        # Select best alternative
        best_alt = alternatives[0]
        
        # Calculate improvement
        improvement_pct = ((best_alt["health_score"] - original_score) / original_score) * 100
        
        # Generate reason
        reason = self._generate_reason(original, best_alt)
        
        # Build nutrition comparison
        nutrition_comparison = {
            "calories": {
                "original": original.get("calories"),
                "alternative": best_alt.get("calories")
            },
            "protein_g": {
                "original": original.get("protein_g"),
                "alternative": best_alt.get("protein_g")
            },
            "sodium_mg": {
                "original": original.get("sodium_mg"),
                "alternative": best_alt.get("sodium_mg")
            }
        }
        
        return HealthyAlternative(
            original_recipe_id=recipe_id,
            original_recipe_title=original["title"],
            original_health_score=original_score,
            alternative_recipe_id=best_alt["id"],
            alternative_recipe_title=best_alt["title"],
            alternative_health_score=best_alt["health_score"],
            improvement_pct=round(improvement_pct, 1),
            reason=reason,
            nutrition_comparison=nutrition_comparison
        )
    
    def find_healthier_alternatives_batch(
        self,
        recipe_ids: List[str],
        dietary_restrictions: Optional[List[DietaryRestriction]] = None,
        allergens: Optional[List[Allergen]] = None
    ) -> List[HealthyAlternative]:
        """
        Find healthier alternatives for multiple recipes
        
        Args:
            recipe_ids: List of recipe IDs
            dietary_restrictions: User's dietary restrictions
            allergens: User's allergens to avoid
        
        Returns:
            List of HealthyAlternative objects
        """
        alternatives = []
        
        for recipe_id in recipe_ids:
            alt = self.find_healthier_alternative(
                recipe_id,
                dietary_restrictions,
                allergens
            )
            if alt:
                alternatives.append(alt)
        
        return alternatives
    
    def _build_dietary_filter(
        self,
        dietary_restrictions: Optional[List[DietaryRestriction]],
        allergens: Optional[List[Allergen]]
    ) -> str:
        """Build Cypher WHERE clause for dietary filtering"""
        conditions = []
        
        if dietary_restrictions:
            restriction_map = {
                DietaryRestriction.VEGETARIAN: "r2.is_vegetarian = true",
                DietaryRestriction.VEGAN: "r2.is_vegan = true",
                DietaryRestriction.PESCATARIAN: "r2.is_pescatarian = true",
                DietaryRestriction.GLUTEN_FREE: "r2.is_gluten_free = true",
                DietaryRestriction.DAIRY_FREE: "r2.is_dairy_free = true",
                DietaryRestriction.KETO: "r2.is_keto_friendly = true",
                DietaryRestriction.PALEO: "r2.is_paleo = true",
                DietaryRestriction.LOW_CARB: "r2.is_low_carb = true",
                DietaryRestriction.HIGH_PROTEIN: "r2.is_high_protein = true"
            }
            
            for restriction in dietary_restrictions:
                if restriction in restriction_map:
                    conditions.append(restriction_map[restriction])
        
        if allergens:
            for allergen in allergens:
                conditions.append(f"NOT '{allergen.value}' IN r2.allergens")
        
        if conditions:
            return "AND " + " AND ".join(conditions)
        return ""
    
    def _generate_reason(self, original: Dict, alternative: Dict) -> str:
        """
        Generate human-readable reason for the alternative
        
        Args:
            original: Original recipe data
            alternative: Alternative recipe data
        
        Returns:
            Reason string
        """
        reasons = []
        
        # Compare calories
        orig_cal = original.get("calories") or 0
        alt_cal = alternative.get("calories") or 0
        if orig_cal > 0 and alt_cal < orig_cal * 0.9:
            cal_savings = orig_cal - alt_cal
            reasons.append(f"{cal_savings} fewer calories")
        
        # Compare sodium
        orig_sodium = original.get("sodium_mg") or 0
        alt_sodium = alternative.get("sodium_mg") or 0
        if orig_sodium > 0 and alt_sodium < orig_sodium * 0.8:
            reasons.append("lower sodium")
        
        # Compare protein
        orig_protein = original.get("protein_g") or 0
        alt_protein = alternative.get("protein_g") or 0
        if alt_protein > orig_protein * 1.2:
            reasons.append("higher protein")
        
        # Health score improvement
        score_diff = alternative["health_score"] - (original.get("health_score") or 5.0)
        reasons.append(f"{score_diff:.1f} point health score improvement")
        
        return ", ".join(reasons)
    
    def suggest_healthiest_recipes(
        self,
        meal_type: Optional[str] = None,
        dietary_restrictions: Optional[List[DietaryRestriction]] = None,
        allergens: Optional[List[Allergen]] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get the healthiest recipes
        
        Args:
            meal_type: Filter by meal type (breakfast, lunch, dinner)
            dietary_restrictions: User's dietary restrictions
            allergens: User's allergens to avoid
            limit: Number of recipes to return
        
        Returns:
            List of recipe dicts
        """
        dietary_filter = self._build_dietary_filter(dietary_restrictions, allergens)
        dietary_filter = dietary_filter.replace("r2.", "r.")  # Adjust for single recipe query
        
        meal_filter = ""
        if meal_type:
            meal_filter = f"AND toLower(r.meal_type) = '{meal_type.lower()}'"
        
        query = f"""
        MATCH (r:Recipe)
        WHERE r.health_score IS NOT NULL
          {meal_filter}
          {dietary_filter}
        RETURN r.id as id,
               r.title as title,
               r.health_score as health_score,
               r.calories_per_serving as calories,
               r.protein_g as protein_g,
               r.is_vegetarian as is_vegetarian,
               r.is_vegan as is_vegan
        ORDER BY r.health_score DESC
        LIMIT $limit
        """
        
        return self.neo4j.execute_query(query, {"limit": limit})


def get_healthy_alternatives_service(neo4j_service: Neo4jService) -> HealthyAlternativesService:
    """Factory function for healthy alternatives service"""
    return HealthyAlternativesService(neo4j_service)

