import re
from typing import List, Dict, Set

class DietaryClassifier:
    """
    Classifies recipes into dietary categories based on their ingredient lists.
    Uses a rule-based approach for high precision (safety first).
    """

    # -------------------------------------------------------------------------
    # Rule Definitions
    # -------------------------------------------------------------------------
    
    # Ingredients that flag a recipe as NOT Vegetarian (Meat, Fish, etc.)
    NON_VEGETARIAN = {
        "chicken", "beef", "pork", "lamb", "turkey", "duck", "bacon", "ham",
        "sausage", "meatball", "steak", "prosciutto", "salami", "pepperoni",
        "fish", "salmon", "tuna", "cod", "shrimp", "prawn", "crab", "lobster",
        "oyster", "clam", "mussel", "anchovy", "gelatin", "lard", "suet"
    }

    # Ingredients that flag a recipe as NOT Vegan (Dairy, Eggs, Honey, etc.)
    # Note: Includes all NON_VEGETARIAN items
    NON_VEGAN = NON_VEGETARIAN | {
        "egg", "eggs", "milk", "butter", "cream", "cheese", "yogurt", "ghee",
        "whey", "casein", "honey", "beeswax", "mayonnaise", "buttermilk"
    }

    # Ingredients that flag a recipe as NOT Gluten-Free
    GLUTEN_CONTAINING = {
        "wheat", "barley", "rye", "flour", "bread", "pasta", "couscous",
        "semolina", "spelt", "farro", "bulgur", "cracker", "cookie", "cake",
        "soy sauce", "seitan", "malt", "beer"
    }

    # Ingredients that flag a recipe as NOT Dairy-Free
    DAIRY_CONTAINING = {
        "milk", "butter", "cream", "cheese", "yogurt", "ghee", "whey", 
        "casein", "lactose", "curd", "buttermilk", "ice cream"
    }

    # Common Allergens
    ALLERGENS = {
        "peanut": {"peanut", "peanut butter"},
        "tree_nut": {"almond", "walnut", "cashew", "pecan", "pistachio", "macadamia", "hazelnut"},
        "soy": {"soy", "tofu", "tempeh", "edamame", "miso", "natto"},
        "fish": {"fish", "salmon", "tuna", "cod", "trout", "halibut"},
        "shellfish": {"shrimp", "crab", "lobster", "clam", "mussel", "oyster", "prawn"},
        "egg": {"egg", "eggs", "mayonnaise", "meringue"},
        "dairy": DAIRY_CONTAINING,
        "gluten": GLUTEN_CONTAINING
    }

    def __init__(self):
        # Pre-compile regex patterns for faster matching (optional optimization)
        pass

    def classify(self, ingredients: List[str]) -> Dict[str, any]:
        """
        Analyze a list of ingredients and return dietary tags.
        
        Args:
            ingredients: List of ingredient strings (e.g. ["1 cup flour", "2 eggs"])
            
        Returns:
            Dictionary with boolean flags and recognized allergens.
        """
        # Normalize ingredients: lowercase, remove punctuation/numbers for checking
        normalized_ings = self._normalize_ingredients(ingredients)
        
        # Check constraints
        is_vegetarian = self._check_safety(normalized_ings, self.NON_VEGETARIAN)
        is_vegan = self._check_safety(normalized_ings, self.NON_VEGAN)
        is_gluten_free = self._check_safety(normalized_ings, self.GLUTEN_CONTAINING)
        is_dairy_free = self._check_safety(normalized_ings, self.DAIRY_CONTAINING)
        
        # Check allergens
        detected_allergens = []
        for allergen, keywords in self.ALLERGENS.items():
            if not self._check_safety(normalized_ings, keywords):
                detected_allergens.append(allergen)

        return {
            "is_vegetarian": is_vegetarian,
            "is_vegan": is_vegan,
            "is_gluten_free": is_gluten_free,
            "is_dairy_free": is_dairy_free,
            "allergens": detected_allergens,
            "ingredient_count": len(ingredients)
        }

    def _normalize_ingredients(self, ingredients: List[str]) -> Set[str]:
        """Convert '2 cups of All-Purpose Flour' -> 'flour' tokens set"""
        tokens = set()
        for ing in ingredients:
            # Lowercase
            text = ing.lower()
            # Simple tokenization by splitting on spaces and removing non-alpha
            words = re.findall(r'[a-z]+', text)
            tokens.update(words)
        return tokens

    def _check_safety(self, ingredient_tokens: Set[str], forbidden_tokens: Set[str]) -> bool:
        """
        Returns True if SAFE (no forbidden tokens found), False otherwise.
        """
        # Intersection finds if any forbidden token exists in ingredients
        # Note: This is a strict check. "coconut milk" containing "milk" is a false positive 
        # that would need exception handling in a production version.
        
        # Refined check: Exact token matches
        # intersection = ingredient_tokens.intersection(forbidden_tokens)
        
        for token in ingredient_tokens:
            if token in forbidden_tokens:
                # Exception logic could go here (e.g. if token == "milk" and "coconut" in ingredient_tokens)
                return False
        return True
