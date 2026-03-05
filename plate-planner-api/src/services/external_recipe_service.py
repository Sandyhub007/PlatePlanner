"""
External Recipe Service — Spoonacular API Integration
=====================================================
Provides a parallel recipe search layer backed by Spoonacular's
380K+ recipes across 80+ cuisines.

Strategy:
  • Cuisine specified  → complexSearch (native cuisine filter + ingredients)
  • No cuisine         → findByIngredients + informationBulk (best ingredient match)

Used as a confidence-based fallback when the local FAISS index
returns sparse or low-confidence results, or when the user
specifies a cuisine not well-covered by the local dataset.
"""

import os
import logging
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("plate_planner.external_recipes")

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
SPOONACULAR_BASE_URL = "https://api.spoonacular.com"

_MAX_CANDIDATES = 20

# Map our dietary bools → Spoonacular diet string
_DIET_MAP = {
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "gluten_free": "gluten free",
    "dairy_free": "dairy free",
}


def _build_diet_param(is_vegan: bool, is_vegetarian: bool,
                      is_gluten_free: bool, is_dairy_free: bool) -> Optional[str]:
    """Return the most restrictive single Spoonacular diet string, or None."""
    if is_vegan:
        return "vegan"
    if is_vegetarian:
        return "vegetarian"
    if is_gluten_free:
        return "gluten free"
    if is_dairy_free:
        return "dairy free"
    return None


def _compute_overlap(input_ingredients: list[str], recipe_ingredients: list[str]) -> list[str]:
    """Return input ingredients that appear (substring) in any recipe ingredient."""
    norm_inputs = [i.lower().strip() for i in input_ingredients]
    matched = []
    for inp in norm_inputs:
        for r_ing in recipe_ingredients:
            if inp in r_ing.lower():
                matched.append(inp)
                break
    return matched


def _extract_instructions(info: dict) -> str:
    """Pull plain-text instructions from a Spoonacular recipe info dict."""
    raw = info.get("instructions") or ""
    # Strip HTML tags if present
    if "<" in raw:
        import re
        raw = re.sub(r"<[^>]+>", " ", raw).strip()
    if raw:
        return raw
    analyzed = info.get("analyzedInstructions", [])
    if analyzed:
        steps = analyzed[0].get("steps", [])
        return "\n".join(
            f"{s.get('number', '')}. {s.get('step', '')}" for s in steps
        ).strip()
    return ""


def _normalize(info: dict, used_ings: list[str], all_ings: list[str],
               total_input: int, image_override: str = "") -> dict:
    """Build a RecipeResult-compatible dict from Spoonacular info."""
    used_count = len(used_ings)
    total_recipe_ings = max(len(all_ings), 1)
    overlap_score = min(used_count / max(total_input, 1), 1.0)
    sem_score = min(used_count / total_recipe_ings, 1.0)
    combined_score = max(0.0, min(1.0, 0.4 * sem_score + 0.6 * overlap_score))

    return {
        "title": info.get("title", "Unknown"),
        "ingredients": used_ings,
        "all_ingredients": all_ings,
        "directions": _extract_instructions(info),
        "semantic_score": round(sem_score, 4),
        "overlap_score": round(overlap_score, 4),
        "combined_score": round(combined_score, 4),
        "rank": 0,
        "source": "spoonacular",
        "cuisine": info.get("cuisines", []),
        "source_url": info.get("sourceUrl", ""),
        "image": image_override or info.get("image", ""),
        "tags": {
            "vegan": info.get("vegan", False),
            "vegetarian": info.get("vegetarian", False),
            "gluten_free": info.get("glutenFree", False),
            "dairy_free": info.get("dairyFree", False),
        },
    }


class SpoonacularService:
    """
    Searches Spoonacular for recipes by ingredient list.
    Returns results normalized to PlatePlanner's RecipeResult format.
    """

    def __init__(self, api_key: str = SPOONACULAR_API_KEY):
        self.api_key = api_key
        self.enabled = bool(api_key)
        if not self.enabled:
            logger.warning(
                "SPOONACULAR_API_KEY not set — external recipe search disabled. "
                "Add it to your .env file to enable wider cuisine coverage."
            )

    async def search_by_ingredients(
        self,
        ingredients: list[str],
        top_n: int = 5,
        cuisine: Optional[str] = None,
        is_vegan: bool = False,
        is_vegetarian: bool = False,
        is_gluten_free: bool = False,
        is_dairy_free: bool = False,
    ) -> list[dict]:
        """
        Route to the best Spoonacular endpoint based on whether a cuisine is specified:
          • cuisine → complexSearch  (native cuisine filter, single API call)
          • no cuisine → findByIngredients + informationBulk (best ingredient ranking)
        """
        if not self.enabled:
            return []

        if cuisine:
            results = await self._complex_search(
                ingredients, top_n, cuisine,
                is_vegan, is_vegetarian, is_gluten_free, is_dairy_free,
            )
        else:
            results = await self._ingredient_search(
                ingredients, top_n,
                is_vegan, is_vegetarian, is_gluten_free, is_dairy_free,
            )

        logger.info(
            f"Spoonacular returned {len(results)} results "
            f"(cuisine={cuisine}, ingredients={ingredients[:3]}...)"
        )
        return results

    # ── Route A: cuisine-aware search via complexSearch ────────────────────
    async def _complex_search(
        self,
        ingredients: list[str],
        top_n: int,
        cuisine: str,
        is_vegan: bool,
        is_vegetarian: bool,
        is_gluten_free: bool,
        is_dairy_free: bool,
    ) -> list[dict]:
        """
        Uses /recipes/complexSearch with cuisine + includeIngredients.
        Returns full recipe info in a single call (addRecipeInformation=true).
        """
        fetch_n = min(top_n * 3, _MAX_CANDIDATES)
        diet = _build_diet_param(is_vegan, is_vegetarian, is_gluten_free, is_dairy_free)
        total_input = max(len(ingredients), 1)

        params = {
            "apiKey": self.api_key,
            "cuisine": cuisine,
            "includeIngredients": ",".join(ingredients),
            "number": fetch_n,
            "addRecipeInformation": True,
            "fillIngredients": True,
            "sort": "max-used-ingredients",
            "ranking": 2,
        }
        if diet:
            params["diet"] = diet

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{SPOONACULAR_BASE_URL}/recipes/complexSearch",
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 402:
                    logger.warning("Spoonacular quota exceeded")
                else:
                    logger.error(f"Spoonacular complexSearch HTTP error: {e}")
                return []
            except Exception as e:
                logger.error(f"Spoonacular complexSearch failed: {e}")
                return []

        results = []
        for recipe in data.get("results", []):
            # Compute overlap from extendedIngredients
            ext_ings = [i.get("name", "") for i in recipe.get("extendedIngredients", [])]
            used_ings = _compute_overlap(ingredients, ext_ings)
            all_ings = ext_ings if ext_ings else ingredients

            result = _normalize(recipe, used_ings, all_ings, total_input,
                                 image_override=recipe.get("image", ""))
            results.append(result)

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results[:top_n]

    # ── Route B: ingredient-first search via findByIngredients ────────────
    async def _ingredient_search(
        self,
        ingredients: list[str],
        top_n: int,
        is_vegan: bool,
        is_vegetarian: bool,
        is_gluten_free: bool,
        is_dairy_free: bool,
    ) -> list[dict]:
        """
        Uses /recipes/findByIngredients (best ingredient-match ranking)
        then /recipes/informationBulk for full details + dietary flags.
        """
        fetch_n = min(top_n * 3, _MAX_CANDIDATES)
        total_input = max(len(ingredients), 1)

        async with httpx.AsyncClient(timeout=12.0) as client:
            # Step 1: find by ingredients
            try:
                resp = await client.get(
                    f"{SPOONACULAR_BASE_URL}/recipes/findByIngredients",
                    params={
                        "apiKey": self.api_key,
                        "ingredients": ",".join(ingredients),
                        "number": fetch_n,
                        "ranking": 2,
                        "ignorePantry": True,
                    },
                )
                resp.raise_for_status()
                candidates = resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 402:
                    logger.warning("Spoonacular quota exceeded")
                else:
                    logger.error(f"Spoonacular findByIngredients HTTP error: {e}")
                return []
            except Exception as e:
                logger.error(f"Spoonacular findByIngredients failed: {e}")
                return []

            if not candidates:
                return []

            # Step 2: bulk info for dietary flags + instructions
            recipe_ids = [str(r["id"]) for r in candidates]
            info_map: dict[int, dict] = {}
            try:
                info_resp = await client.get(
                    f"{SPOONACULAR_BASE_URL}/recipes/informationBulk",
                    params={
                        "apiKey": self.api_key,
                        "ids": ",".join(recipe_ids),
                        "includeNutrition": False,
                    },
                )
                info_resp.raise_for_status()
                info_map = {r["id"]: r for r in info_resp.json()}
            except Exception as e:
                logger.warning(f"Spoonacular informationBulk failed: {e}")

        results = []
        for candidate in candidates:
            recipe_id = candidate["id"]
            info = info_map.get(recipe_id, {})

            # Dietary hard-filters
            if is_vegan and not info.get("vegan", False):
                continue
            if is_vegetarian and not info.get("vegetarian", False):
                continue
            if is_gluten_free and not info.get("glutenFree", False):
                continue
            if is_dairy_free and not info.get("dairyFree", False):
                continue

            used_ings = [i["name"] for i in candidate.get("usedIngredients", [])]
            missed_ings = [i["name"] for i in candidate.get("missedIngredients", [])]
            all_ings = used_ings + missed_ings

            result = _normalize(
                info,
                used_ings, all_ings, total_input,
                image_override=candidate.get("image", ""),
            )
            results.append(result)

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results[:top_n]


# Module-level singleton
spoonacular = SpoonacularService()
