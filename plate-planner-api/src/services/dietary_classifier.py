"""
Dietary Classification Service
Automatically classifies recipes based on ingredients
"""
import logging
from typing import List, Dict, Set, Tuple
from src.services.neo4j_service import Neo4jService
from src.schemas.nutrition import DietaryRestriction, Allergen

logger = logging.getLogger(__name__)


class DietaryClassifier:
    """
    Classifies recipes and ingredients for dietary restrictions and allergens
    """
    
    # Ingredient keywords for dietary classification
    ANIMAL_PRODUCTS = {
        "meat", "beef", "pork", "lamb", "veal", "chicken", "turkey", "duck",
        "fish", "salmon", "tuna", "cod", "tilapia", "shrimp", "crab", "lobster",
        "egg", "dairy", "milk", "cheese", "butter", "cream", "yogurt", "honey"
    }
    
    MEAT_KEYWORDS = {
        "meat", "beef", "pork", "lamb", "veal", "chicken", "turkey", "duck",
        "bacon", "sausage", "ham", "steak", "ground beef", "ribs"
    }
    
    SEAFOOD_KEYWORDS = {
        "fish", "salmon", "tuna", "cod", "tilapia", "halibut", "trout",
        "shrimp", "crab", "lobster", "scallop", "oyster", "clam", "mussel",
        "anchovy", "sardine", "mackerel"
    }
    
    DAIRY_KEYWORDS = {
        "milk", "cheese", "butter", "cream", "yogurt", "whey", "casein",
        "mozzarella", "cheddar", "parmesan", "brie", "feta", "ricotta",
        "ice cream", "sour cream", "half and half"
    }
    
    EGG_KEYWORDS = {
        "egg", "eggs", "mayonnaise", "mayo"
    }
    
    GLUTEN_KEYWORDS = {
        "wheat", "flour", "bread", "pasta", "couscous", "semolina",
        "barley", "rye", "malt", "seitan", "breadcrumb", "crouton",
        "soy sauce"  # Most soy sauce contains wheat
    }
    
    # Allergen keywords
    ALLERGEN_KEYWORDS = {
        Allergen.NUTS: {"almond", "walnut", "cashew", "pecan", "hazelnut", "macadamia", "pistachio", "nut"},
        Allergen.PEANUTS: {"peanut", "peanut butter"},
        Allergen.TREE_NUTS: {"almond", "walnut", "cashew", "pecan", "hazelnut", "macadamia", "pistachio"},
        Allergen.DAIRY: DAIRY_KEYWORDS,
        Allergen.EGGS: EGG_KEYWORDS,
        Allergen.GLUTEN: GLUTEN_KEYWORDS,
        Allergen.WHEAT: {"wheat", "flour"},
        Allergen.SOY: {"soy", "tofu", "tempeh", "edamame", "miso"},
        Allergen.FISH: {"fish", "salmon", "tuna", "cod", "tilapia", "halibut", "trout", "anchovy", "sardine"},
        Allergen.SHELLFISH: {"shrimp", "crab", "lobster", "scallop", "oyster", "clam", "mussel"},
        Allergen.SESAME: {"sesame", "tahini"}
    }
    
    # High protein ingredients (>20g per 100g)
    HIGH_PROTEIN_INGREDIENTS = {
        "chicken breast", "turkey breast", "tuna", "salmon", "cod",
        "egg white", "tofu", "tempeh", "greek yogurt", "cottage cheese",
        "lentils", "chickpeas", "black beans", "quinoa"
    }
    
    # Keto-friendly characteristics
    KETO_AVOID = {
        "bread", "pasta", "rice", "potato", "corn", "flour", "sugar",
        "honey", "fruit", "banana", "apple", "orange", "oatmeal"
    }
    
    def __init__(self, neo4j_service: Neo4jService):
        """
        Initialize dietary classifier
        
        Args:
            neo4j_service: Neo4j service for querying recipes
        """
        self.neo4j = neo4j_service
    
    def classify_recipe(self, recipe_id: str) -> Dict[str, any]:
        """
        Classify a recipe for dietary restrictions and allergens
        
        Args:
            recipe_id: Neo4j recipe ID
        
        Returns:
            Dict with dietary classifications
        """
        # Get recipe ingredients
        query = """
        MATCH (r:Recipe {id: $recipe_id})-[:HAS_INGREDIENT]->(i:Ingredient)
        RETURN r.title as title,
               collect(toLower(i.name)) as ingredients
        """
        result = self.neo4j.execute_query(query, {"recipe_id": recipe_id})
        
        if not result:
            logger.warning(f"Recipe not found: {recipe_id}")
            return self._default_classification()
        
        ingredients = result[0]["ingredients"]
        title = result[0]["title"]
        
        # Classify
        classification = {
            "is_vegetarian": self._is_vegetarian(ingredients),
            "is_vegan": self._is_vegan(ingredients),
            "is_pescatarian": self._is_pescatarian(ingredients),
            "is_gluten_free": self._is_gluten_free(ingredients),
            "is_dairy_free": self._is_dairy_free(ingredients),
            "is_keto_friendly": self._is_keto_friendly(ingredients),
            "is_paleo": self._is_paleo(ingredients),
            "is_low_carb": False,  # Requires nutrition data
            "is_high_protein": self._is_high_protein(ingredients),
            "allergens": self._detect_allergens(ingredients)
        }
        
        logger.info(f"Classified recipe '{title}': vegetarian={classification['is_vegetarian']}, "
                   f"vegan={classification['is_vegan']}, allergens={classification['allergens']}")
        
        return classification
    
    def _is_vegetarian(self, ingredients: List[str]) -> bool:
        """Check if recipe is vegetarian (no meat or fish)"""
        ingredients_text = " ".join(ingredients)
        
        # Check for meat or seafood
        for keyword in self.MEAT_KEYWORDS | self.SEAFOOD_KEYWORDS:
            if keyword in ingredients_text:
                return False
        
        return True
    
    def _is_vegan(self, ingredients: List[str]) -> bool:
        """Check if recipe is vegan (no animal products)"""
        ingredients_text = " ".join(ingredients)
        
        # Check for any animal products
        for keyword in self.ANIMAL_PRODUCTS:
            if keyword in ingredients_text:
                return False
        
        return True
    
    def _is_pescatarian(self, ingredients: List[str]) -> bool:
        """Check if recipe is pescatarian (no meat, fish allowed)"""
        ingredients_text = " ".join(ingredients)
        
        # Check for meat (but fish is okay)
        for keyword in self.MEAT_KEYWORDS:
            if keyword in ingredients_text:
                return False
        
        return True
    
    def _is_gluten_free(self, ingredients: List[str]) -> bool:
        """Check if recipe is gluten-free"""
        ingredients_text = " ".join(ingredients)
        
        for keyword in self.GLUTEN_KEYWORDS:
            if keyword in ingredients_text:
                return False
        
        return True
    
    def _is_dairy_free(self, ingredients: List[str]) -> bool:
        """Check if recipe is dairy-free"""
        ingredients_text = " ".join(ingredients)
        
        for keyword in self.DAIRY_KEYWORDS:
            if keyword in ingredients_text:
                return False
        
        return True
    
    def _is_keto_friendly(self, ingredients: List[str]) -> bool:
        """Check if recipe is keto-friendly (low carb, high fat)"""
        ingredients_text = " ".join(ingredients)
        
        # Check for high-carb ingredients
        carb_count = 0
        for keyword in self.KETO_AVOID:
            if keyword in ingredients_text:
                carb_count += 1
        
        # If more than 1 high-carb ingredient, likely not keto
        return carb_count <= 1
    
    def _is_paleo(self, ingredients: List[str]) -> bool:
        """Check if recipe is paleo (no grains, dairy, legumes)"""
        ingredients_text = " ".join(ingredients)
        
        # Paleo excludes grains, dairy, legumes, processed foods
        paleo_avoid = {
            "bread", "pasta", "rice", "wheat", "flour", "oat",
            "milk", "cheese", "yogurt", "butter",
            "beans", "lentils", "chickpea", "peanut",
            "soy", "tofu"
        }
        
        for keyword in paleo_avoid:
            if keyword in ingredients_text:
                return False
        
        return True
    
    def _is_high_protein(self, ingredients: List[str]) -> bool:
        """Check if recipe has high-protein ingredients"""
        ingredients_text = " ".join(ingredients)
        
        # Count high-protein ingredients
        protein_count = 0
        for ingredient in self.HIGH_PROTEIN_INGREDIENTS:
            if ingredient in ingredients_text:
                protein_count += 1
        
        return protein_count >= 2
    
    def _detect_allergens(self, ingredients: List[str]) -> List[str]:
        """Detect allergens in recipe"""
        ingredients_text = " ".join(ingredients)
        allergens = []
        
        for allergen, keywords in self.ALLERGEN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in ingredients_text:
                    allergens.append(allergen.value)
                    break
        
        return list(set(allergens))  # Remove duplicates
    
    def _default_classification(self) -> Dict[str, any]:
        """Default classification when recipe not found"""
        return {
            "is_vegetarian": False,
            "is_vegan": False,
            "is_pescatarian": False,
            "is_gluten_free": False,
            "is_dairy_free": False,
            "is_keto_friendly": False,
            "is_paleo": False,
            "is_low_carb": False,
            "is_high_protein": False,
            "allergens": []
        }
    
    def classify_all_recipes(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Classify all recipes in Neo4j database
        
        Args:
            batch_size: Number of recipes to process at once
        
        Returns:
            Statistics dict
        """
        # Get all recipe IDs
        query = "MATCH (r:Recipe) RETURN r.id as id"
        results = self.neo4j.execute_query(query)
        
        if not results:
            logger.warning("No recipes found to classify")
            return {"total": 0, "classified": 0}
        
        recipe_ids = [r["id"] for r in results]
        total = len(recipe_ids)
        classified = 0
        
        logger.info(f"Classifying {total} recipes...")
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch = recipe_ids[i:i+batch_size]
            
            for recipe_id in batch:
                classification = self.classify_recipe(recipe_id)
                
                # Update Neo4j
                self._update_recipe_classification(recipe_id, classification)
                classified += 1
            
            logger.info(f"Classified {classified}/{total} recipes")
        
        logger.info(f"Classification complete: {classified} recipes")
        return {"total": total, "classified": classified}
    
    def _update_recipe_classification(self, recipe_id: str, classification: Dict[str, any]):
        """Update recipe classification in Neo4j"""
        query = """
        MATCH (r:Recipe {id: $recipe_id})
        SET r.is_vegetarian = $is_vegetarian,
            r.is_vegan = $is_vegan,
            r.is_pescatarian = $is_pescatarian,
            r.is_gluten_free = $is_gluten_free,
            r.is_dairy_free = $is_dairy_free,
            r.is_keto_friendly = $is_keto_friendly,
            r.is_paleo = $is_paleo,
            r.is_low_carb = $is_low_carb,
            r.is_high_protein = $is_high_protein,
            r.allergens = $allergens
        """
        
        params = {
            "recipe_id": recipe_id,
            **classification
        }
        
        try:
            self.neo4j.execute_query(query, params)
        except Exception as e:
            logger.error(f"Error updating recipe {recipe_id}: {e}")
    
    def filter_recipes_by_dietary_needs(
        self,
        dietary_restrictions: List[DietaryRestriction],
        allergens: List[Allergen]
    ) -> str:
        """
        Generate Cypher WHERE clause for dietary filtering
        
        Args:
            dietary_restrictions: User's dietary restrictions
            allergens: User's allergens to avoid
        
        Returns:
            Cypher WHERE clause string
        """
        conditions = []
        
        # Map dietary restrictions to recipe properties
        restriction_map = {
            DietaryRestriction.VEGETARIAN: "r.is_vegetarian = true",
            DietaryRestriction.VEGAN: "r.is_vegan = true",
            DietaryRestriction.PESCATARIAN: "r.is_pescatarian = true",
            DietaryRestriction.GLUTEN_FREE: "r.is_gluten_free = true",
            DietaryRestriction.DAIRY_FREE: "r.is_dairy_free = true",
            DietaryRestriction.KETO: "r.is_keto_friendly = true",
            DietaryRestriction.PALEO: "r.is_paleo = true",
            DietaryRestriction.LOW_CARB: "r.is_low_carb = true",
            DietaryRestriction.HIGH_PROTEIN: "r.is_high_protein = true"
        }
        
        # Add dietary restriction conditions
        for restriction in dietary_restrictions:
            if restriction in restriction_map:
                conditions.append(restriction_map[restriction])
        
        # Add allergen conditions (must NOT contain allergen)
        for allergen in allergens:
            conditions.append(f"NOT '{allergen.value}' IN r.allergens")
        
        # Build WHERE clause
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""


def get_dietary_classifier(neo4j_service: Neo4jService) -> DietaryClassifier:
    """Factory function for dietary classifier"""
    return DietaryClassifier(neo4j_service)

