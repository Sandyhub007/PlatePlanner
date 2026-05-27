"""
Pantry-Aware Ingredient Substitution Service

Given a recipe's ingredients and the user's pantry, this service:
1. Identifies which ingredients the user HAS vs is MISSING
2. For each MISSING ingredient, queries Neo4j for substitutes
3. Splits substitutes into "from your pantry" vs "other" (need to buy)
"""

import logging
from typing import Optional

import os

logger = logging.getLogger("plate_planner.substitution")

W2V_PATH = "src/data/models/ingredient_substitution/ingredient_w2v.model"
w2v_model = None
try:
    if os.path.exists(W2V_PATH):
        from gensim.models import Word2Vec
        w2v_model = Word2Vec.load(W2V_PATH)
except Exception as e:
    logger.warning(f"Could not load Word2Vec model: {e}")

def _get_neo4j_driver():
    return None

def _is_neo4j_available(driver) -> bool:
    return w2v_model is not None


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
            
        # 3. Simple plural handling: pantry "egg" matches recipe "eggs"
        pattern_plural = r'\b' + re.escape(p_item) + r'(s|es)?\b'
        if re.search(pattern_plural, ing_lower):
            return True

        # 4. Reverse plural: pantry "eggs" matches recipe "egg"
        if p_item.endswith('es') and len(p_item) > 3:
            base = p_item[:-2]
            if re.search(r'\b' + re.escape(base) + r'\b', ing_lower):
                return True
        elif p_item.endswith('s') and len(p_item) > 2:
            base = p_item[:-1]
            if re.search(r'\b' + re.escape(base) + r'\b', ing_lower):
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

            # Only query Model if it's available
            if w2v_model is not None:
                try:
                    ing_lower = ingredient.lower().strip()
                    query_word = ing_lower
                    if query_word not in w2v_model.wv:
                        for w in query_word.split():
                            if w in w2v_model.wv:
                                query_word = w
                                break
                    
                    subs = []
                    if query_word in w2v_model.wv:
                        similar = w2v_model.wv.most_similar(query_word, topn=top_k * 4)
                        for name, score in similar:
                            if name == ing_lower or name in ing_lower or ing_lower in name:
                                continue
                            subs.append({
                                "name": name,
                                "score": float(score),
                                "source": "w2v"
                            })

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

def get_w2v_substitutes(ingredient: str, top_k: int = 5) -> list[dict]:
    if w2v_model is None:
        return []
    
    ing_lower = ingredient.lower().strip()
    query_word = ing_lower
    if query_word not in w2v_model.wv:
        for w in query_word.split():
            if w in w2v_model.wv:
                query_word = w
                break
    
    subs = []
    if query_word in w2v_model.wv:
        similar = w2v_model.wv.most_similar(query_word, topn=top_k * 4)
        for name, score in similar:
            if name == ing_lower or name in ing_lower or ing_lower in name:
                continue
            subs.append({
                "name": name,
                "score": float(score),
                "source": "w2v",
                "context": None
            })
    return subs[:top_k]
