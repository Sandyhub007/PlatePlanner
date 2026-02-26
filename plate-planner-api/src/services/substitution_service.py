"""
Pantry-Aware Ingredient Substitution Service

Given a recipe's ingredients and the user's pantry, this service:
1. Identifies which ingredients the user HAS vs is MISSING
2. For each MISSING ingredient, queries Neo4j for substitutes
3. Splits substitutes into "from your pantry" vs "other" (need to buy)
"""

import logging
from typing import Optional

from src.evaluation.hybrid_substitution import normalize_ingredient, get_hybrid_subs

logger = logging.getLogger("plate_planner.substitution")


def _get_neo4j_driver():
    """Lazy import to avoid circular imports and allow graceful failure."""
    try:
        from src.services.neo4j_service import driver
        return driver
    except Exception:
        return None


def _is_neo4j_available(driver) -> bool:
    """Quick TCP socket check if Neo4j port is reachable (1s timeout)."""
    if driver is None:
        return False
    import socket
    try:
        sock = socket.create_connection(("localhost", 7687), timeout=1.0)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        logger.warning("Neo4j is not reachable on port 7687 — substitution lookups will be skipped")
        return False


import re

def _fuzzy_match(pantry_tokens: set[str], ingredient: str) -> bool:
    """
    Check if an ingredient is 'in' the pantry using word-boundary matching.
    """
    ing_lower = ingredient.lower().strip()
    for pantry_item in pantry_tokens:
        p_item = pantry_item.lower().strip()
        if not p_item: continue
        
        # 1. Exact match (fast)
        if p_item == ing_lower: return True
        
        # 2. Match as whole word substring
        # e.g. "chicken" matches "chicken breast"
        # escaped = re.escape(p_item)
        # Using \b to ensure we match "onion" in "green onion" but NOT "corn" in "popcorn"
        pattern = r'\b' + re.escape(p_item) + r'\b'
        if re.search(pattern, ing_lower):
            return True
            
        # 3. Simple plural handling: allow pantry item + 's' or 'es' match
        # e.g. pantry "egg" matches "eggs"
        pattern_plural = r'\b' + re.escape(p_item) + r'(s|es)?\b'
        if re.search(pattern_plural, ing_lower):
            return True
            
    return False


def get_pantry_substitutions(
    recipe_ingredients: list[str],
    pantry: list[str],
    top_k: int = 3,
) -> dict:
    """
    Analyze a recipe against the user's pantry and suggest substitutions.

    Args:
        recipe_ingredients: Full ingredient list for the recipe
        pantry: List of ingredients the user has available
        top_k: Number of substitutes to fetch per missing ingredient

    Returns:
        {
            "have": [{"ingredient": "chicken", "matched_as": "chicken breast"}],
            "missing": [
                {
                    "ingredient": "soy sauce",
                    "pantry_substitutes": [{"name": "fish sauce", "score": 0.82}],
                    "other_substitutes": [{"name": "tamari", "score": 0.91}]
                }
            ],
            "total_ingredients": 6,
            "have_count": 2,
            "missing_count": 4,
            "coverage": 0.33
        }
    """
    pantry_lower = {p.lower().strip() for p in pantry if p.strip()}

    # Check Neo4j availability ONCE up front
    driver = _get_neo4j_driver()
    neo4j_available = _is_neo4j_available(driver)

    have = []
    missing = []

    for ingredient in recipe_ingredients:
        if _fuzzy_match(pantry_lower, ingredient):
            have.append({
                "ingredient": ingredient,
                "matched_as": ingredient,
            })
        else:
            missing_entry = {
                "ingredient": ingredient,
                "pantry_substitutes": [],
                "other_substitutes": [],
            }

            # Only query Neo4j if it's available
            if neo4j_available and driver is not None:
                try:
                    norm_ing = normalize_ingredient(ingredient)
                    with driver.session() as session:
                        subs = session.execute_read(
                            get_hybrid_subs, norm_ing, None, top_k * 3
                        )

                    for sub in subs:
                        sub_entry = {
                            "name": sub["name"],
                            "score": round(sub["score"], 4),
                            "source": sub.get("source", "hybrid"),
                        }
                        if _fuzzy_match(pantry_lower, sub["name"]):
                            missing_entry["pantry_substitutes"].append(sub_entry)
                        else:
                            missing_entry["other_substitutes"].append(sub_entry)

                    missing_entry["pantry_substitutes"] = missing_entry["pantry_substitutes"][:top_k]
                    missing_entry["other_substitutes"] = missing_entry["other_substitutes"][:top_k]

                except Exception:
                    logger.warning(f"Could not find substitutes for '{ingredient}'", exc_info=True)

            missing.append(missing_entry)

    total = len(recipe_ingredients)
    have_count = len(have)

    return {
        "have": have,
        "missing": missing,
        "total_ingredients": total,
        "have_count": have_count,
        "missing_count": total - have_count,
        "coverage": round(have_count / max(total, 1), 2),
    }
