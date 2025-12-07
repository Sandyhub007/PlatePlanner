"""Ingredient Name Matching Utility - Phase 3

Handles fuzzy matching of ingredient names for consolidation.
Uses thefuzz library for similarity scoring.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from thefuzz import fuzz, process

# Common ingredient variations and synonyms
INGREDIENT_SYNONYMS: Dict[str, List[str]] = {
    "tomato": ["tomatoes", "cherry tomato", "cherry tomatoes", "roma tomato", "plum tomato"],
    "onion": ["onions", "yellow onion", "white onion", "red onion", "sweet onion"],
    "garlic": ["garlic cloves", "garlic clove", "garlic bulb"],
    "chicken": ["chicken breast", "chicken breasts", "chicken thigh", "chicken thighs", "chicken wing", "chicken wings"],
    "beef": ["ground beef", "beef steak", "beef roast"],
    "milk": ["whole milk", "skim milk", "2% milk", "almond milk", "soy milk"],
    "butter": ["unsalted butter", "salted butter", "margarine"],
    "flour": ["all-purpose flour", "wheat flour", "white flour"],
    "sugar": ["white sugar", "granulated sugar", "brown sugar"],
    "oil": ["olive oil", "vegetable oil", "canola oil", "cooking oil"],
    "pepper": ["black pepper", "ground pepper", "peppercorn"],
    "salt": ["table salt", "sea salt", "kosher salt"],
    "cheese": ["cheddar cheese", "mozzarella cheese", "parmesan cheese"],
    "egg": ["eggs", "large egg", "large eggs"],
    "potato": ["potatoes", "russet potato", "red potato", "sweet potato"],
    "carrot": ["carrots", "baby carrot", "baby carrots"],
    "lettuce": ["iceberg lettuce", "romaine lettuce", "leaf lettuce"],
    "pepper": ["bell pepper", "bell peppers", "red pepper", "green pepper"],
}


def normalize_ingredient_name(name: str) -> str:
    """
    Normalize ingredient name for matching.
    
    Args:
        name: Ingredient name
    
    Returns:
        Normalized name (lowercase, trimmed, singularized where possible)
    """
    name = name.strip().lower()
    
    # Remove common prefixes/suffixes
    name = name.replace("fresh ", "").replace("dried ", "").replace("frozen ", "")
    name = name.replace("chopped ", "").replace("diced ", "").replace("sliced ", "")
    name = name.replace("minced ", "").replace("grated ", "").replace("shredded ", "")
    
    # Remove quantity words
    name = name.replace("a ", "").replace("an ", "").replace("some ", "")
    
    return name.strip()


def are_ingredients_similar(name1: str, name2: str, threshold: int = 85) -> bool:
    """
    Check if two ingredient names are similar enough to be consolidated.
    
    Args:
        name1: First ingredient name
        name2: Second ingredient name
        threshold: Similarity threshold (0-100), default 85
    
    Returns:
        True if ingredients are similar
    """
    norm1 = normalize_ingredient_name(name1)
    norm2 = normalize_ingredient_name(name2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return True
    
    # Check synonyms
    for base, variants in INGREDIENT_SYNONYMS.items():
        if norm1 in [base] + variants and norm2 in [base] + variants:
            return True
    
    # Fuzzy match
    ratio = fuzz.ratio(norm1, norm2)
    partial_ratio = fuzz.partial_ratio(norm1, norm2)
    token_sort_ratio = fuzz.token_sort_ratio(norm1, norm2)
    
    # Use best match
    best_match = max(ratio, partial_ratio, token_sort_ratio)
    
    return best_match >= threshold


def find_similar_ingredient(
    ingredient_name: str,
    candidate_list: List[str],
    threshold: int = 85
) -> Optional[Tuple[str, int]]:
    """
    Find the most similar ingredient from a candidate list.
    
    Args:
        ingredient_name: Ingredient to match
        candidate_list: List of candidate ingredient names
        threshold: Minimum similarity threshold
    
    Returns:
        Tuple of (matched_name, similarity_score) or None
    """
    if not candidate_list:
        return None
    
    # Use process.extractOne for best match
    result = process.extractOne(
        normalize_ingredient_name(ingredient_name),
        [normalize_ingredient_name(c) for c in candidate_list],
        scorer=fuzz.token_sort_ratio
    )
    
    if result and result[1] >= threshold:
        # Find original name (before normalization)
        matched_normalized = result[0]
        for candidate in candidate_list:
            if normalize_ingredient_name(candidate) == matched_normalized:
                return (candidate, result[1])
    
    return None


def group_similar_ingredients(
    ingredients: List[Dict[str, any]],
    threshold: int = 85
) -> List[Dict[str, any]]:
    """
    Group similar ingredients together for consolidation.
    
    Args:
        ingredients: List of ingredient dicts with 'ingredient_name' key
        threshold: Similarity threshold
    
    Returns:
        List of grouped ingredients with consolidated data
    """
    if not ingredients:
        return []
    
    groups: List[Dict[str, any]] = []
    used_indices = set()
    
    for i, ing in enumerate(ingredients):
        if i in used_indices:
            continue
        
        # Start a new group
        group = {
            "ingredient_name": ing["ingredient_name"],
            "normalized_name": normalize_ingredient_name(ing["ingredient_name"]),
            "quantities": [(ing.get("quantity", 1.0), ing.get("unit", "item"))],
            "recipe_references": list(ing.get("recipe_references", [])),
        }
        
        # Find similar ingredients
        for j, other_ing in enumerate(ingredients[i+1:], start=i+1):
            if j in used_indices:
                continue
            
            if are_ingredients_similar(
                ing["ingredient_name"],
                other_ing["ingredient_name"],
                threshold
            ):
                # Add to group
                group["quantities"].append((
                    other_ing.get("quantity", 1.0),
                    other_ing.get("unit", "item")
                ))
                for ref in other_ing.get("recipe_references", []):
                    if ref not in group["recipe_references"]:
                        group["recipe_references"].append(ref)
                
                used_indices.add(j)
        
        groups.append(group)
        used_indices.add(i)
    
    return groups

