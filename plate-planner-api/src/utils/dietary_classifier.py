import re
from typing import List, Dict, Set, Tuple


class DietaryClassifier:
    """
    Classifies recipes into dietary categories based on their ingredient lists.
    Uses an enhanced rule-based approach with compound ingredient awareness.
    
    Key improvements over v1:
    - Compound ingredient exceptions (e.g., "coconut milk" is NOT dairy)
    - Multi-word matching (not just single tokens)
    - Configurable sensitivity
    - Better coverage of modern ingredients
    """

    # ─── Exception Lists (Compound Ingredients) ──────────────────────
    # These override false positives from single-token matching.
    # If a full ingredient string contains one of these, it's NOT flagged.
    
    # Items containing "milk" that are NOT dairy
    NOT_DAIRY_EXCEPTIONS = {
        "coconut milk", "coconut cream", "almond milk", "oat milk",
        "soy milk", "rice milk", "cashew milk", "hemp milk",
        "macadamia milk", "flax milk", "pea milk", "potato milk",
        "coconut yogurt", "soy yogurt", "almond yogurt",
        "vegan butter", "plant butter", "earth balance",
        "vegan cheese", "nutritional yeast", "dairy-free",
        "dairy free", "non-dairy", "nondairy",
        "coconut whipped cream", "oat cream", "soy cream",
        "vegan cream cheese", "cashew cream",
        "coconut ice cream", "soy ice cream",
    }
    
    # Items containing meat words that are NOT meat
    NOT_MEAT_EXCEPTIONS = {
        "coconut bacon", "tempeh bacon", "vegan bacon",
        "jackfruit", "mushroom steak", "cauliflower steak",
        "eggplant steak", "portobello steak",
        "beyond meat", "impossible burger", "plant-based",
        "vegan sausage", "vegan chicken", "vegan turkey",
        "mock duck", "seitan", "textured vegetable protein",
        "tvp", "vegan ham", "tofurky",
        "coconut aminos",  # not "amino" but sounds meaty
        "fish sauce" # will be handled separately as non-veg still
    }
    
    # Items containing gluten words that are NOT gluten
    NOT_GLUTEN_EXCEPTIONS = {
        "gluten-free", "gluten free", "gf flour",
        "gluten-free flour", "rice flour", "almond flour",
        "coconut flour", "tapioca flour", "chickpea flour",
        "oat flour",  # oats can be GF if certified
        "corn flour", "potato flour", "cassava flour",
        "tamari",  # GF soy sauce alternative
        "gluten-free soy sauce", "coconut aminos",
        "rice pasta", "gluten-free pasta", "corn pasta",
        "rice bread", "gluten-free bread",
        "rice cracker", "corn cracker",
        "gluten-free beer",
    }
    
    # Items containing egg words that are NOT egg
    NOT_EGG_EXCEPTIONS = {
        "eggplant", "egg plant", "eggnog-flavored",
        "egg replacer", "vegan egg", "flax egg",
        "chia egg", "aquafaba",  # egg substitute
    }

    # ─── Forbidden Token Sets ────────────────────────────────────────
    
    # Non-vegetarian ingredients (meats, fish, etc.)
    NON_VEGETARIAN_TOKENS = {
        "chicken", "beef", "pork", "lamb", "turkey", "duck", "bacon",
        "ham", "sausage", "meatball", "steak", "prosciutto", "salami",
        "pepperoni", "veal", "venison", "bison", "rabbit", "goat",
        "fish", "salmon", "tuna", "cod", "shrimp", "prawn", "crab",
        "lobster", "oyster", "clam", "mussel", "anchovy", "anchovies",
        "sardine", "sardines", "scallop", "squid", "calamari",
        "octopus", "tilapia", "trout", "halibut", "mahi",
        "gelatin", "lard", "suet", "tallow", "bone broth",
        "worcestershire",  # contains anchovies
    }
    
    # Non-vegetarian multi-word patterns (checked as substrings)
    NON_VEGETARIAN_PATTERNS = [
        "chicken breast", "ground beef", "ground turkey", "pork chop",
        "pork loin", "beef broth", "chicken broth", "chicken stock",
        "beef stock", "fish sauce", "oyster sauce", "bone marrow",
    ]

    # Non-vegan (includes all non-vegetarian + animal products)
    NON_VEGAN_TOKENS = NON_VEGETARIAN_TOKENS | {
        "egg", "eggs", "milk", "butter", "cream", "cheese", "yogurt",
        "yoghurt", "ghee", "whey", "casein", "honey", "beeswax",
        "mayonnaise", "mayo", "buttermilk", "custard", "meringue",
        "marshmallow",  # contains gelatin
        "lard",
    }

    # Gluten-containing
    GLUTEN_TOKENS = {
        "wheat", "barley", "rye", "flour", "bread", "pasta",
        "couscous", "semolina", "spelt", "farro", "bulgur",
        "cracker", "cookie", "cake", "noodle", "noodles",
        "soy sauce", "seitan", "malt", "beer", "breadcrumbs",
        "panko", "tortilla", "pita", "croissant", "pastry",
        "pie crust", "biscuit", "wafer",
    }

    # Dairy-containing
    DAIRY_TOKENS = {
        "milk", "butter", "cream", "cheese", "yogurt", "yoghurt",
        "ghee", "whey", "casein", "lactose", "curd", "buttermilk",
        "ice cream", "sour cream", "cream cheese", "ricotta",
        "mozzarella", "parmesan", "cheddar", "brie", "gouda",
        "feta", "mascarpone", "gruyere", "provolone",
        "half and half", "half-and-half", "heavy cream",
        "whipped cream", "evaporated milk", "condensed milk",
        "powdered milk", "skim milk", "whole milk",
    }

    # Common Allergens (expanded)
    ALLERGENS = {
        "peanut": {
            "tokens": {"peanut", "peanut butter", "peanut oil"},
            "exceptions": set(),
        },
        "tree_nut": {
            "tokens": {
                "almond", "walnut", "cashew", "pecan", "pistachio",
                "macadamia", "hazelnut", "pine nut", "brazil nut",
                "chestnut", "praline",
            },
            "exceptions": {"coconut"},  # technically a drupe, not tree nut
        },
        "soy": {
            "tokens": {"soy", "tofu", "tempeh", "edamame", "miso", "natto"},
            "exceptions": {"soy sauce"},  # handled separately in gluten check
        },
        "fish": {
            "tokens": {"fish", "salmon", "tuna", "cod", "trout", "halibut",
                       "tilapia", "mahi", "sardine", "anchovy"},
            "exceptions": set(),
        },
        "shellfish": {
            "tokens": {"shrimp", "crab", "lobster", "clam", "mussel",
                       "oyster", "prawn", "scallop", "crawfish"},
            "exceptions": set(),
        },
        "egg": {
            "tokens": {"egg", "eggs", "mayonnaise", "mayo", "meringue"},
            "exceptions": {"eggplant", "egg plant", "egg replacer", "vegan egg"},
        },
        "dairy": {
            "tokens": DAIRY_TOKENS,
            "exceptions": NOT_DAIRY_EXCEPTIONS,
        },
        "gluten": {
            "tokens": GLUTEN_TOKENS,
            "exceptions": NOT_GLUTEN_EXCEPTIONS,
        },
    }

    def __init__(self):
        # Pre-compile exception patterns for faster matching
        self._dairy_exception_patterns = [
            re.compile(r'\b' + re.escape(exc) + r'\b', re.IGNORECASE)
            for exc in self.NOT_DAIRY_EXCEPTIONS
        ]
        self._meat_exception_patterns = [
            re.compile(r'\b' + re.escape(exc) + r'\b', re.IGNORECASE)
            for exc in self.NOT_MEAT_EXCEPTIONS
        ]
        self._gluten_exception_patterns = [
            re.compile(r'\b' + re.escape(exc) + r'\b', re.IGNORECASE)
            for exc in self.NOT_GLUTEN_EXCEPTIONS
        ]
        self._egg_exception_patterns = [
            re.compile(r'\b' + re.escape(exc) + r'\b', re.IGNORECASE)
            for exc in self.NOT_EGG_EXCEPTIONS
        ]

    def classify(self, ingredients: List[str]) -> Dict[str, any]:
        """
        Analyze a list of ingredients and return dietary tags.
        
        Args:
            ingredients: List of ingredient strings (e.g., ["1 cup flour", "2 eggs"])
            
        Returns:
            Dictionary with boolean flags and recognized allergens.
        """
        # Check each dietary constraint
        is_vegetarian = self._check_vegetarian(ingredients)
        is_vegan = self._check_vegan(ingredients)
        is_gluten_free = self._check_gluten_free(ingredients)
        is_dairy_free = self._check_dairy_free(ingredients)
        
        # Check allergens
        detected_allergens = []
        for allergen, config in self.ALLERGENS.items():
            if self._has_allergen(ingredients, config["tokens"], config.get("exceptions", set())):
                detected_allergens.append(allergen)

        return {
            "is_vegetarian": is_vegetarian,
            "is_vegan": is_vegan,
            "is_gluten_free": is_gluten_free,
            "is_dairy_free": is_dairy_free,
            "allergens": detected_allergens,
            "ingredient_count": len(ingredients),
        }

    def _normalize_ingredient(self, ing: str) -> str:
        """Normalize an ingredient string for matching."""
        # Remove quantities, measurements, and special characters
        text = ing.lower().strip()
        # Remove leading numbers and fractions
        text = re.sub(r'^[\d\s/½⅓¼¾⅔⅛⅜⅝⅞.,-]+', '', text)
        # Remove common measurement words
        text = re.sub(
            r'\b(cup|cups|tablespoon|tablespoons|tbsp|teaspoon|teaspoons|tsp|'
            r'pound|pounds|lb|lbs|ounce|ounces|oz|gram|grams|kg|ml|liter|liters|'
            r'pinch|dash|bunch|sprig|clove|cloves|can|cans|package|packages|'
            r'slice|slices|piece|pieces|large|small|medium|fresh|dried|chopped|'
            r'minced|diced|sliced|crushed|ground|whole|optional)\b',
            '', text
        )
        return text.strip()

    def _ingredient_matches_token(self, ingredient_text: str, token: str) -> bool:
        """Check if an ingredient contains a forbidden token as a whole word."""
        pattern = r'\b' + re.escape(token) + r'\b'
        return bool(re.search(pattern, ingredient_text))

    def _has_exception(self, ingredient_text: str, exception_patterns: list) -> bool:
        """Check if an ingredient matches any exception pattern."""
        for pattern in exception_patterns:
            if pattern.search(ingredient_text):
                return True
        return False

    def _check_vegetarian(self, ingredients: List[str]) -> bool:
        """Returns True if recipe appears vegetarian."""
        for ing in ingredients:
            text = self._normalize_ingredient(ing)
            
            # Check if this ingredient matches an exception first
            if self._has_exception(text, self._meat_exception_patterns):
                continue
            
            # Check single tokens
            for token in self.NON_VEGETARIAN_TOKENS:
                if self._ingredient_matches_token(text, token):
                    return False
            
            # Check multi-word patterns
            for pattern in self.NON_VEGETARIAN_PATTERNS:
                if pattern in text:
                    return False
        
        return True

    def _check_vegan(self, ingredients: List[str]) -> bool:
        """Returns True if recipe appears vegan."""
        for ing in ingredients:
            text = self._normalize_ingredient(ing)
            
            # Check exceptions for dairy, meat, and egg
            has_dairy_exc = self._has_exception(text, self._dairy_exception_patterns)
            has_meat_exc = self._has_exception(text, self._meat_exception_patterns)
            has_egg_exc = self._has_exception(text, self._egg_exception_patterns)
            
            for token in self.NON_VEGAN_TOKENS:
                if self._ingredient_matches_token(text, token):
                    # Check if this is a false positive (compound ingredient)
                    if token in {"milk", "cream", "butter", "cheese", "yogurt", 
                                 "yoghurt", "whey", "ice cream"} and has_dairy_exc:
                        continue
                    if token in self.NON_VEGETARIAN_TOKENS and has_meat_exc:
                        continue
                    if token in {"egg", "eggs", "mayonnaise", "mayo"} and has_egg_exc:
                        continue
                    return False
        
        return True

    def _check_gluten_free(self, ingredients: List[str]) -> bool:
        """Returns True if recipe appears gluten-free."""
        for ing in ingredients:
            text = self._normalize_ingredient(ing)
            
            # Check exceptions first
            if self._has_exception(text, self._gluten_exception_patterns):
                continue
            
            for token in self.GLUTEN_TOKENS:
                if self._ingredient_matches_token(text, token):
                    return False
        
        return True

    def _check_dairy_free(self, ingredients: List[str]) -> bool:
        """Returns True if recipe appears dairy-free."""
        for ing in ingredients:
            text = self._normalize_ingredient(ing)
            
            # Check exceptions first
            if self._has_exception(text, self._dairy_exception_patterns):
                continue
            
            for token in self.DAIRY_TOKENS:
                if self._ingredient_matches_token(text, token):
                    return False
        
        return True

    def _has_allergen(
        self, ingredients: List[str], tokens: Set[str], exceptions: Set[str]
    ) -> bool:
        """Check if any ingredient contains an allergen token (with exceptions)."""
        exception_patterns = [
            re.compile(r'\b' + re.escape(exc) + r'\b', re.IGNORECASE)
            for exc in exceptions
        ] if exceptions else []
        
        for ing in ingredients:
            text = self._normalize_ingredient(ing)
            
            # Skip if exception matches
            if exception_patterns and any(p.search(text) for p in exception_patterns):
                continue
            
            for token in tokens:
                if self._ingredient_matches_token(text, token):
                    return True
        
        return False
