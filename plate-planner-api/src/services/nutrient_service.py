from typing import List, Dict

class NutrientService:
    """
    Stage 3: Nutrient Scoring (Optimization)
    Mathematically ranks candidate recipes by scoring how closely their nutritional 
    profile aligns with the user's specific meal goals.
    """
    def __init__(self):
        pass

    def rank_by_nutrition(self, safe_recipes: List[Dict], user_goals: Dict) -> List[Dict]:
        """
        Takes a list of safe recipes and ranks them mathematically based on Euclidean 
        distance from the user's target goals (e.g., target_calories).
        
        Args:
            safe_recipes: List of dictionaries (from ontology_service)
            user_goals: Dictionary containing targets like {'target_calories': 500}
        """
        if not safe_recipes:
            return []
            
        target_calories = user_goals.get("target_calories")
        
        if not target_calories:
            # If no specific goal is set, maintain the incoming semantic rank
            return safe_recipes

        # In a full production scenario, recipes.db would also contain protein, carbs, fats.
        # Here we optimize on `calories_per_serving` if it exists in the dictionary,
        # or simulate it if not fetched from sqlite. 
        # (Note: we should ideally fetch calories in Stage 1 Retrieval)
        
        scored_recipes = []
        for recipe in safe_recipes:
            # Retrieve calories if fetched, else assign a default average meal value (e.g., 600)
            recipe_cals = recipe.get("calories_per_serving") or 600.0
            
            # Simple Euclidean distance (1D) for calories
            # The lower the distance, the better the fit.
            calorie_distance = abs(recipe_cals - target_calories)
            
            # Combine nutritional distance with semantic score
            # We normalize distance: max acceptable deviation is roughly 500 cals
            norm_cal_penalty = min(calorie_distance / 500.0, 1.0)
            
            # Original semantic score (High is good, usually 0-1)
            sem_score = recipe.get("semantic_score", 0.0)
            
            # Heuristic fitness score: Semantic strongly dictates relevance, but 
            # we penalize heavily if macro targets are missed.
            fitness_score = sem_score - (norm_cal_penalty * 0.5)
            
            # Attach score back to recipe metadata
            recipe["fitness_score"] = float(fitness_score)
            recipe["calorie_distance"] = float(calorie_distance)
            scored_recipes.append(recipe)
            
        # Rank by fitness score descending (highest fitness first)
        scored_recipes.sort(key=lambda x: x["fitness_score"], reverse=True)
        
        return scored_recipes

# Singleton instance
nutrient_service = NutrientService()
