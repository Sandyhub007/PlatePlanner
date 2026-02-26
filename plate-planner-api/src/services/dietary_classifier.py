"""
Dietary Classification Service (v2 — Enhanced)
Automatically classifies recipes based on ingredients.

Key improvements:
- Compound ingredient awareness (e.g., "coconut milk" is NOT dairy)
- Word-boundary matching instead of substring matching
- Exception lists for plant-based alternatives
"""
import re
import logging
from typing import List, Dict, Set, Tuple
from src.services.neo4j_service import Neo4jService
from src.schemas.nutrition import DietaryRestriction, Allergen

logger = logging.getLogger(__name__)


class DietaryClassifier:
    """
    Classifies recipes and ingredients for dietary restrictions and allergens.
    Uses compound-ingredient–aware matching to avoid false positives.
    """
    
    # ─── Exception Lists (false-positive protection) ─────────────────
    # If ANY of these appear in the full ingredient string, the token match
    # is treated as a false positive and ignored.
    
    DAIRY_EXCEPTIONS = {
        "coconut milk", "coconut cream", "almond milk", "oat milk",
        "soy milk", "rice milk", "cashew milk", "hemp milk",
        "macadamia milk", "flax milk", "coconut yogurt", "soy yogurt",
        "almond yogurt", "vegan butter", "plant butter",
        "vegan cheese", "coconut whipped cream", "oat cream",
        "soy cream", "cashew cream", "vegan cream cheese",
        "coconut ice cream", "soy ice cream", "dairy-free", "dairy free",
        "non-dairy", "nondairy", "nutritional yeast",
    }
    
    MEAT_EXCEPTIONS = {
        "coconut bacon", "tempeh bacon", "vegan bacon",
        "jackfruit", "mushroom steak", "cauliflower steak",
        "eggplant steak", "portobello steak",
        "beyond meat", "impossible burger", "plant-based",
        "vegan sausage", "vegan chicken", "vegan turkey",
        "mock duck", "tofurky", "vegan ham",
        "coconut aminos",
    }
    
    EGG_EXCEPTIONS = {
        "eggplant", "egg plant", "egg replacer", "vegan egg",
        "flax egg", "chia egg", "aquafaba",
    }
    
    GLUTEN_EXCEPTIONS = {
        "gluten-free", "gluten free", "rice flour", "almond flour",
        "coconut flour", "tapioca flour", "chickpea flour",
        "corn flour", "potato flour", "cassava flour",
        "tamari", "gluten-free soy sauce", "coconut aminos",
        "rice pasta", "gluten-free pasta", "corn pasta",
        "rice bread", "gluten-free bread",
        "gluten-free beer",
    }
    
    # ─── Ingredient keyword sets ─────────────────────────────────────
    
    ANIMAL_PRODUCTS = {
        "meat", "beef", "pork", "lamb", "veal", "chicken", "turkey", "duck",
        "fish", "salmon", "tuna", "cod", "tilapia", "shrimp", "crab", "lobster",
        "egg", "dairy", "milk", "cheese", "butter", "cream", "yogurt", "honey",
    }
    
    MEAT_KEYWORDS = {
        "meat", "beef", "pork", "lamb", "veal", "chicken", "turkey", "duck",
        "bacon", "sausage", "ham", "steak", "ribs", "prosciutto", "salami",
        "pepperoni", "venison", "bison", "rabbit", "goat",
        "gelatin", "lard", "suet", "tallow",
    }
    
    MEAT_PHRASES = [
        "ground beef", "ground turkey", "chicken breast", "pork chop",
        "pork loin", "beef broth", "chicken broth", "chicken stock",
        "beef stock", "bone broth", "bone marrow",
    ]
    
    SEAFOOD_KEYWORDS = {
        "fish", "salmon", "tuna", "cod", "tilapia", "halibut", "trout",
        "shrimp", "crab", "lobster", "scallop", "oyster", "clam", "mussel",
        "anchovy", "anchovies", "sardine", "sardines", "mackerel",
        "squid", "calamari", "octopus", "prawn",
    }
    
    SEAFOOD_PHRASES = [
        "fish sauce", "oyster sauce",
    ]
    
    DAIRY_KEYWORDS = {
        "milk", "cheese", "butter", "cream", "yogurt", "yoghurt",
        "whey", "casein", "ghee", "buttermilk", "lactose",
        "mozzarella", "cheddar", "parmesan", "brie", "feta", "ricotta",
        "mascarpone", "gruyere", "provolone", "gouda",
        "ice cream", "sour cream", "half and half", "half-and-half",
        "heavy cream", "whipped cream", "evaporated milk",
        "condensed milk", "cream cheese",
    }
    
    EGG_KEYWORDS = {
        "egg", "eggs", "mayonnaise", "mayo", "meringue",
    }
    
    GLUTEN_KEYWORDS = {
        "wheat", "flour", "bread", "pasta", "couscous", "semolina",
        "barley", "rye", "malt", "seitan", "breadcrumb", "breadcrumbs",
        "crouton", "panko", "noodle", "noodles",
        "soy sauce", "tortilla", "pita", "pastry", "pie crust",
        "spelt", "farro", "bulgur",
    }
    
    # Allergen keywords
    ALLERGEN_KEYWORDS = {
        Allergen.NUTS: {
            "tokens": {"almond", "walnut", "cashew", "pecan", "hazelnut", "macadamia", "pistachio", "nut"},
            "exceptions": {"coconut"},
        },
        Allergen.PEANUTS: {
            "tokens": {"peanut", "peanut butter"},
            "exceptions": set(),
        },
        Allergen.TREE_NUTS: {
            "tokens": {"almond", "walnut", "cashew", "pecan", "hazelnut", "macadamia", "pistachio"},
            "exceptions": {"coconut"},
        },
        Allergen.DAIRY: {
            "tokens": DAIRY_KEYWORDS,
            "exceptions": DAIRY_EXCEPTIONS,
        },
        Allergen.EGGS: {
            "tokens": EGG_KEYWORDS,
            "exceptions": EGG_EXCEPTIONS,
        },
        Allergen.GLUTEN: {
            "tokens": GLUTEN_KEYWORDS,
            "exceptions": GLUTEN_EXCEPTIONS,
        },
        Allergen.WHEAT: {
            "tokens": {"wheat", "flour"},
            "exceptions": {"rice flour", "almond flour", "coconut flour", "tapioca flour",
                           "chickpea flour", "corn flour", "potato flour", "cassava flour"},
        },
        Allergen.SOY: {
            "tokens": {"soy", "tofu", "tempeh", "edamame", "miso"},
            "exceptions": set(),
        },
        Allergen.FISH: {
            "tokens": {"fish", "salmon", "tuna", "cod", "tilapia", "halibut", "trout", "anchovy", "sardine"},
            "exceptions": set(),
        },
        Allergen.SHELLFISH: {
            "tokens": {"shrimp", "crab", "lobster", "scallop", "oyster", "clam", "mussel"},
            "exceptions": set(),
        },
        Allergen.SESAME: {
            "tokens": {"sesame", "tahini"},
            "exceptions": set(),
        },
    }
    
    # High protein ingredients (>20g per 100g)
    HIGH_PROTEIN_INGREDIENTS = {
        "chicken breast", "turkey breast", "tuna", "salmon", "cod",
        "egg white", "tofu", "tempeh", "greek yogurt", "cottage cheese",
        "lentils", "chickpeas", "black beans", "quinoa",
    }
    
    # Keto-unfriendly
    KETO_AVOID = {
        "bread", "pasta", "rice", "potato", "corn", "flour", "sugar",
        "honey", "fruit", "banana", "apple", "orange", "oatmeal",
    }
    
    def __init__(self, neo4j_service: Neo4jService):
        """
        Initialize dietary classifier
        
        Args:
            neo4j_service: Neo4j service for querying recipes
        """
        self.neo4j = neo4j_service
        
        # Pre-compile exception patterns for performance
        self._dairy_exc_patterns = self._compile_exceptions(self.DAIRY_EXCEPTIONS)
        self._meat_exc_patterns = self._compile_exceptions(self.MEAT_EXCEPTIONS)
        self._egg_exc_patterns = self._compile_exceptions(self.EGG_EXCEPTIONS)
        self._gluten_exc_patterns = self._compile_exceptions(self.GLUTEN_EXCEPTIONS)
    
    @staticmethod
    def _compile_exceptions(exceptions: set) -> list:
        """Pre-compile regex patterns for fast exception matching."""
        return [
            re.compile(r'\b' + re.escape(exc) + r'\b', re.IGNORECASE)
            for exc in exceptions
        ]
    
    @staticmethod
    def _has_exception(text: str, patterns: list) -> bool:
        """Check if text matches any exception pattern."""
        return any(p.search(text) for p in patterns)
    
    @staticmethod
    def _word_match(text: str, keyword: str) -> bool:
        """Check for whole-word match (prevents substring false positives)."""
        return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))
    
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
            "allergens": self._detect_allergens(ingredients),
        }
        
        logger.info(
            f"Classified recipe '{title}': vegetarian={classification['is_vegetarian']}, "
            f"vegan={classification['is_vegan']}, allergens={classification['allergens']}"
        )
        
        return classification
    
    def _is_vegetarian(self, ingredients: List[str]) -> bool:
        """Check if recipe is vegetarian (no meat or fish)."""
        for ing in ingredients:
            # Check exceptions first
            if self._has_exception(ing, self._meat_exc_patterns):
                continue
            
            for keyword in self.MEAT_KEYWORDS | self.SEAFOOD_KEYWORDS:
                if self._word_match(ing, keyword):
                    return False
            
            for phrase in self.MEAT_PHRASES + self.SEAFOOD_PHRASES:
                if phrase in ing:
                    return False
        
        return True
    
    def _is_vegan(self, ingredients: List[str]) -> bool:
        """Check if recipe is vegan (no animal products)."""
        for ing in ingredients:
            has_dairy_exc = self._has_exception(ing, self._dairy_exc_patterns)
            has_meat_exc = self._has_exception(ing, self._meat_exc_patterns)
            has_egg_exc = self._has_exception(ing, self._egg_exc_patterns)
            
            for keyword in self.ANIMAL_PRODUCTS:
                if self._word_match(ing, keyword):
                    # Check compound exceptions
                    if keyword in self.DAIRY_KEYWORDS and has_dairy_exc:
                        continue
                    if keyword in (self.MEAT_KEYWORDS | self.SEAFOOD_KEYWORDS) and has_meat_exc:
                        continue
                    if keyword in self.EGG_KEYWORDS and has_egg_exc:
                        continue
                    return False
        
        return True
    
    def _is_pescatarian(self, ingredients: List[str]) -> bool:
        """Check if recipe is pescatarian (no meat, fish allowed)."""
        for ing in ingredients:
            if self._has_exception(ing, self._meat_exc_patterns):
                continue
            
            for keyword in self.MEAT_KEYWORDS:
                if self._word_match(ing, keyword):
                    return False
            
            for phrase in self.MEAT_PHRASES:
                if phrase in ing:
                    return False
        
        return True
    
    def _is_gluten_free(self, ingredients: List[str]) -> bool:
        """Check if recipe is gluten-free."""
        for ing in ingredients:
            if self._has_exception(ing, self._gluten_exc_patterns):
                continue
            
            for keyword in self.GLUTEN_KEYWORDS:
                if self._word_match(ing, keyword):
                    return False
        
        return True
    
    def _is_dairy_free(self, ingredients: List[str]) -> bool:
        """Check if recipe is dairy-free."""
        for ing in ingredients:
            if self._has_exception(ing, self._dairy_exc_patterns):
                continue
            
            for keyword in self.DAIRY_KEYWORDS:
                if self._word_match(ing, keyword):
                    return False
        
        return True
    
    def _is_keto_friendly(self, ingredients: List[str]) -> bool:
        """Check if recipe is keto-friendly (low carb, high fat)."""
        carb_count = 0
        for ing in ingredients:
            for keyword in self.KETO_AVOID:
                if self._word_match(ing, keyword):
                    carb_count += 1
                    break
        
        return carb_count <= 1
    
    def _is_paleo(self, ingredients: List[str]) -> bool:
        """Check if recipe is paleo (no grains, dairy, legumes)."""
        paleo_avoid = {
            "bread", "pasta", "rice", "wheat", "flour", "oat",
            "milk", "cheese", "yogurt", "butter",
            "beans", "lentils", "chickpea", "peanut",
            "soy", "tofu",
        }
        
        for ing in ingredients:
            # Apply dairy + gluten exceptions
            if self._has_exception(ing, self._dairy_exc_patterns):
                continue
            if self._has_exception(ing, self._gluten_exc_patterns):
                continue
            
            for keyword in paleo_avoid:
                if self._word_match(ing, keyword):
                    return False
        
        return True
    
    def _is_high_protein(self, ingredients: List[str]) -> bool:
        """Check if recipe has high-protein ingredients."""
        ingredients_text = " ".join(ingredients)
        
        protein_count = 0
        for ingredient in self.HIGH_PROTEIN_INGREDIENTS:
            if ingredient in ingredients_text:
                protein_count += 1
        
        return protein_count >= 2
    
    def _detect_allergens(self, ingredients: List[str]) -> List[str]:
        """Detect allergens in recipe with compound-ingredient awareness."""
        allergens = []
        
        for allergen, config in self.ALLERGEN_KEYWORDS.items():
            tokens = config["tokens"]
            exceptions = config.get("exceptions", set())
            
            # Compile exception patterns
            exc_patterns = self._compile_exceptions(exceptions) if exceptions else []
            
            found = False
            for ing in ingredients:
                if exc_patterns and self._has_exception(ing, exc_patterns):
                    continue
                
                for keyword in tokens:
                    if self._word_match(ing, keyword):
                        found = True
                        break
                if found:
                    break
            
            if found:
                allergens.append(allergen.value)
        
        return list(set(allergens))
    
    def _default_classification(self) -> Dict[str, any]:
        """Default classification when recipe not found."""
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
            "allergens": [],
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
        
        for i in range(0, total, batch_size):
            batch = recipe_ids[i:i+batch_size]
            
            for recipe_id in batch:
                classification = self.classify_recipe(recipe_id)
                self._update_recipe_classification(recipe_id, classification)
                classified += 1
            
            logger.info(f"Classified {classified}/{total} recipes")
        
        logger.info(f"Classification complete: {classified} recipes")
        return {"total": total, "classified": classified}
    
    def _update_recipe_classification(self, recipe_id: str, classification: Dict[str, any]):
        """Update recipe classification in Neo4j."""
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
            **classification,
        }
        
        try:
            self.neo4j.execute_query(query, params)
        except Exception as e:
            logger.error(f"Error updating recipe {recipe_id}: {e}")
    
    def filter_recipes_by_dietary_needs(
        self,
        dietary_restrictions: List[DietaryRestriction],
        allergens: List[Allergen],
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
        
        restriction_map = {
            DietaryRestriction.VEGETARIAN: "r.is_vegetarian = true",
            DietaryRestriction.VEGAN: "r.is_vegan = true",
            DietaryRestriction.PESCATARIAN: "r.is_pescatarian = true",
            DietaryRestriction.GLUTEN_FREE: "r.is_gluten_free = true",
            DietaryRestriction.DAIRY_FREE: "r.is_dairy_free = true",
            DietaryRestriction.KETO: "r.is_keto_friendly = true",
            DietaryRestriction.PALEO: "r.is_paleo = true",
            DietaryRestriction.LOW_CARB: "r.is_low_carb = true",
            DietaryRestriction.HIGH_PROTEIN: "r.is_high_protein = true",
        }
        
        for restriction in dietary_restrictions:
            if restriction in restriction_map:
                conditions.append(restriction_map[restriction])
        
        for allergen in allergens:
            conditions.append(f"NOT '{allergen.value}' IN r.allergens")
        
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""


def get_dietary_classifier(neo4j_service: Neo4jService) -> DietaryClassifier:
    """Factory function for dietary classifier"""
    return DietaryClassifier(neo4j_service)
