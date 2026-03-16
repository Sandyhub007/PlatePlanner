import asyncio
import csv
import difflib
import logging
import os
import re
import unicodedata
from collections import defaultdict
from typing import List, Optional
from ast import literal_eval

from fastapi import FastAPI, HTTPException, Query, status, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.services.neo4j_service import get_hybrid_substitutes, recipe_details as fetch_recipe_details
from src.services.substitution_service import get_pantry_substitutions
from src.services.external_recipe_service import spoonacular
from src.utils.recipesuggestionmodel import suggest_recipes, DB_PATH
import sqlite3
import json
from src.api.routers import auth, users, meal_plans, shopping_lists, nutrition, recommendations, user_meals, pantry
from src.database.session import engine, Base
from src.database.schema_guards import ensure_phase_two_schema, ensure_phase_three_schema, ensure_pantry_schema, ensure_meal_log_schema, ensure_onboarding_schema
from src.config.paths import DataPaths

# ——— Database Initialization ———
Base.metadata.create_all(bind=engine)
ensure_phase_two_schema()
ensure_phase_three_schema()  # Phase 3: Shopping Lists
ensure_pantry_schema()        # Pantry
ensure_meal_log_schema()      # Meal logging
ensure_onboarding_schema()    # Onboarding flag

# ——— FastAPI app setup ———
app = FastAPI(
    title="Plate Planner Backend",
    version="0.5",  # Phase 4A: Nutritional Analysis & Health Dashboard
    openapi_tags=[
        {"name": "health", "description": "Health check"},
        {"name": "authentication", "description": "User registration and login"},
        {"name": "users", "description": "User profile and preferences"},
        {"name": "meal-plans", "description": "AI-powered weekly meal planning"},
        {"name": "shopping-lists", "description": "Shopping list generation and management"},
        {"name": "nutrition", "description": "Nutritional analysis, health tracking, and goals"},
        {"name": "recipes", "description": "Recipe suggestion operations"},
        {"name": "substitution", "description": "Ingredient substitution operations"},
        {"name": "AI Assistant", "description": "AI-powered recipe adaptation, meal planning, and cooking tips"},
    ],
)

# ——— CORS ———
# Configure allowed origins via the CORS_ORIGINS environment variable.
# In production, set a comma-separated list of allowed origins, e.g.:
#   CORS_ORIGINS=https://plateplanner.vercel.app,https://www.plateplanner.com
# When CORS_ORIGINS is not set, all origins are allowed (development default).
_cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
_cors_origins = (
    ["*"] if _cors_origins_raw.strip() == "*"
    else [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ——— Routers ———
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(meal_plans.router)
app.include_router(shopping_lists.router)
app.include_router(nutrition.router)
app.include_router(recommendations.router)
app.include_router(user_meals.router)
app.include_router(pantry.router)

# ——— Logging ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("plate_planner")

# ——— RAG AI Assistant Router (graceful if LLM not configured) ———
try:
    from src.services.rag_service import create_rag_router
    app.include_router(create_rag_router())
    logger.info("🤖 AI Assistant endpoints enabled (/ai/*)")
except Exception as e:
    logger.warning(f"AI Assistant endpoints not available: {e}")


# ——— Models ———
class RecipeRequest(BaseModel):
    """Incoming request payload for recipe suggestions."""
    ingredients: List[str] = Field(
        ...,
        description="List of ingredients to base the recipe suggestions on",
        example=["butter", "sugar", "flour"],
    )
    top_n: int = Field(
        5,
        description="Number of top recipes to return",
        example=5,
    )
    rerank_weight: float = Field(
        0.6,
        description="Balance between semantic similarity and ingredient overlap (0–1)",
        example=0.6,
    )
    
    # Dietary filters
    is_vegan: bool = Field(False, description="Filter for vegan recipes")
    is_vegetarian: bool = Field(False, description="Filter for vegetarian recipes")
    is_gluten_free: bool = Field(False, description="Filter for gluten-free recipes")
    is_dairy_free: bool = Field(False, description="Filter for dairy-free recipes")

    # Category / meal type filter
    category: Optional[str] = Field(
        None,
        description="Recipe category or meal type filter (e.g. 'breakfast', 'lunch', 'dinner', 'dessert', 'appetizer', 'snack')",
        example="dinner",
    )

    # Extended search options
    cuisine: Optional[str] = Field(
        None,
        description="Cuisine filter (e.g. 'Italian', 'Japanese', 'Indian'). "
                    "When set, Spoonacular external search is always included.",
        example="Thai",
    )
    enable_external: bool = Field(
        True,
        description="Allow Spoonacular external search when local results are sparse or low-confidence",
    )
    enable_llm_fallback: bool = Field(
        True,
        description="Generate a recipe via LLM when no good matches are found anywhere",
    )

    class Config:
        schema_extra = {
            "examples": {
                "🍪 Basic Baking": {
                    "summary": "Common baking ingredients",
                    "value": {"ingredients": ["butter", "sugar", "flour"]}
                },
                "🥗 Light Salad": {
                    "summary": "Simple salad base",
                    "value": {"ingredients": ["lettuce", "tomato", "olive oil"]}
                },
                "🍝 Pasta Dinner": {
                    "summary": "Pasta plus flavorings",
                    "value": {"ingredients": ["pasta", "garlic", "parmesan"]}
                },
                "🌱 Vegan Check": {
                    "summary": "Vegan stir fry search",
                    "value": {
                        "ingredients": ["tofu", "broccoli", "soy sauce"],
                        "is_vegan": True
                    }
                }
            }
        }


class RecipeResult(BaseModel):
    """Schema for a single suggested recipe."""
    title: str
    # only those that overlapped with the query
    ingredients: List[str]
    all_ingredients: List[str] = []
    directions: str = ""
    semantic_score: float
    overlap_score: float
    combined_score: float
    rank: int
    tags: Optional[dict] = None
    # Extended fields for external/LLM results
    source: str = "local"
    cuisine: List[str] = []
    source_url: str = ""
    image: str = ""


class RecipeSuggestionResponse(BaseModel):
    """Outgoing response for suggested recipes."""
    input_ingredients: List[str]
    top_n: int
    results: List[RecipeResult]


class SubstituteItem(BaseModel):
    name: str = Field(..., description="Substitute ingredient name", example="oleo")
    score: float = Field(..., description="Normalized similarity score (0–1)", example=0.83)
    context: Optional[str] = Field(None, description="Context in which this substitute applies", example="baking")
    source: str = Field(..., description="Whether this came from 'direct', 'cooccurrence' or 'hybrid'", example="direct")


class SubstituteResponse(BaseModel):
    ingredient: str = Field(..., description="Original ingredient you looked up", example="butter")
    context: Optional[str] = Field(None, description="Optional usage context", example="baking")
    hybrid: bool = Field(..., description="Whether hybrid lookup was used", example=False)
    substitutes: List[SubstituteItem] = Field(..., description="List of candidate substitutions")


class RecipeDetails(BaseModel):
    title: str = Field(..., example="Marinated Flank Steak Recipe")
    directions: list[str] = Field(
        ..., description="Step-by-step cooking instructions"
    )
    link: str = Field(
        ..., description="URL to the original recipe"
    )
    source: str = Field(..., example="Recipes1M")
    ingredients: list[str] = Field(
        ...,
        description="Full ingredient list, deduplicated & in original order",
    )


# ——— Pantry Substitution Models ———
class PantrySubstituteItem(BaseModel):
    name: str = Field(..., description="Name of the substitute ingredient")
    score: float = Field(..., description="Similarity score (0–1)")
    source: str = Field("hybrid", description="Source of the substitution")


class MissingIngredient(BaseModel):
    ingredient: str = Field(..., description="The missing ingredient")
    pantry_substitutes: List[PantrySubstituteItem] = Field(
        default=[], description="Substitutes the user already has in their pantry"
    )
    other_substitutes: List[PantrySubstituteItem] = Field(
        default=[], description="Other possible substitutes (need to buy)"
    )


class HaveIngredient(BaseModel):
    ingredient: str = Field(..., description="Ingredient the user has")
    matched_as: str = Field(..., description="How it matched in the recipe")


class PantrySubstitutionRequest(BaseModel):
    pantry: List[str] = Field(
        ...,
        description="List of ingredients the user has available",
        example=["chicken", "rice", "garlic", "onion", "fish sauce", "honey"]
    )


class PantrySubstitutionResponse(BaseModel):
    recipe_title: str
    total_ingredients: int
    have_count: int
    missing_count: int
    coverage: float = Field(..., description="Fraction of ingredients user already has (0–1)")
    have: List[HaveIngredient]
    missing: List[MissingIngredient]


# ——— Fuzzy Title Deduplication Helpers ———
def _normalize_title(title: str) -> str:
    """
    Canonical form used for fast-path exact dedup:
      • lowercase
      • unicode → ASCII (café → cafe)
      • strip punctuation / hyphens / extra whitespace
      • sort words alphabetically (handles "Lemon Rosemary" vs "Rosemary Lemon")
    """
    t = title.lower()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-z0-9\s]", " ", t)   # drop punctuation
    t = re.sub(r"\s+", " ", t).strip()
    return " ".join(sorted(t.split()))    # sort words


def _is_duplicate_title(
    candidate: str,
    seen_normalized: list[str],
    threshold: float = 0.82,
) -> bool:
    """
    Return True if *candidate* is too similar to any already-seen title.

    Two-stage check (fast-path first):
      1. Normalized exact match (handles hyphens, punctuation, word-order).
      2. SequenceMatcher ratio on the *original* lowercased titles.
    """
    norm_candidate = _normalize_title(candidate)
    if norm_candidate in seen_normalized:
        return True
    # Fuzzy fallback — only run against titles whose first word matches
    # to keep O(n) manageable on large result sets
    low = candidate.lower()
    for norm in seen_normalized:
        ratio = difflib.SequenceMatcher(None, low, norm, autojunk=False).ratio()
        if ratio >= threshold:
            return True
    return False


# ——— Endpoints ———
@app.get("/", tags=["health"], summary="Health check")
async def root() -> dict:
    return {"message": "Plate Planner API is running."}


@app.post(
    "/suggest_recipes",
    response_model=List[RecipeResult],
    status_code=status.HTTP_200_OK,
    summary="Suggest recipes — federated search (local FAISS + Spoonacular + LLM fallback)",
    tags=["recipes"],
)
async def suggest_recipes_endpoint(request: RecipeRequest):
    """
    Three-tier federated recipe search:
      1. Local FAISS (2M recipes, fastest)
      2. Spoonacular API (380K+ recipes, 80+ cuisines) — triggered when cuisine is set,
         local results are sparse, or combined_score falls below 0.35
      3. LLM generation — triggered when combined results are still fewer than 2
         or max score is below 0.25
    """
    # ── Tier 1: Local FAISS search ────────────────────────────────────────
    try:
        local_results = await asyncio.to_thread(
            suggest_recipes,
            request.ingredients,
            request.top_n,
            request.rerank_weight,
            500,  # raw_k
            2,    # min_overlap
            request.is_vegan,
            request.is_vegetarian,
            request.is_gluten_free,
            request.is_dairy_free,
        )
    except Exception:
        logger.exception("Local FAISS search failed")
        local_results = []

    # Tag local results with source
    for r in local_results:
        r.setdefault("source", "local")
        r.setdefault("cuisine", [])
        r.setdefault("source_url", "")
        r.setdefault("image", "")

    # Decide whether to trigger external search
    _LOCAL_CONFIDENCE_THRESHOLD = 0.35
    max_local_score = max((r["combined_score"] for r in local_results), default=0.0)
    needs_external = (
        request.enable_external
        and spoonacular.enabled
        and (
            request.cuisine is not None           # cuisine explicitly requested
            or len(local_results) < request.top_n # not enough local results
            or max_local_score < _LOCAL_CONFIDENCE_THRESHOLD  # low confidence
        )
    )

    # ── Tier 2: Spoonacular external search (parallel when triggered) ─────
    external_results: list[dict] = []
    if needs_external:
        try:
            external_results = await spoonacular.search_by_ingredients(
                ingredients=request.ingredients,
                top_n=request.top_n,
                cuisine=request.cuisine,
                is_vegan=request.is_vegan,
                is_vegetarian=request.is_vegetarian,
                is_gluten_free=request.is_gluten_free,
                is_dairy_free=request.is_dairy_free,
            )
        except Exception:
            logger.exception("Spoonacular search failed — continuing with local results")

    # ── Merge and de-duplicate (fuzzy title matching) ─────────────────────
    seen_normalized: list[str] = []   # list preserves insertion order for ratio checks
    merged: list[dict] = []
    for result in local_results + external_results:
        if not _is_duplicate_title(result["title"], seen_normalized):
            seen_normalized.append(_normalize_title(result["title"]))
            merged.append(result)

    merged.sort(key=lambda x: x["combined_score"], reverse=True)
    merged = merged[:request.top_n]

    # ── Tier 3: LLM generation fallback ──────────────────────────────────
    _LLM_TRIGGER_THRESHOLD = 0.25
    max_merged_score = max((r["combined_score"] for r in merged), default=0.0)
    needs_llm = (
        request.enable_llm_fallback
        and (len(merged) < 2 or max_merged_score < _LLM_TRIGGER_THRESHOLD)
    )

    if needs_llm:
        try:
            from src.services.rag_service import RAGService
            rag = RAGService()
            llm_results = await rag.generate_recipe(
                ingredients=request.ingredients,
                cuisine=request.cuisine,
                is_vegan=request.is_vegan,
                is_vegetarian=request.is_vegetarian,
                is_gluten_free=request.is_gluten_free,
                is_dairy_free=request.is_dairy_free,
                top_n=max(request.top_n - len(merged), 1),
            )
            for r in llm_results:
                if not _is_duplicate_title(r["title"], seen_normalized):
                    seen_normalized.append(_normalize_title(r["title"]))
                    merged.append(r)
            merged.sort(key=lambda x: x["combined_score"], reverse=True)
            merged = merged[:request.top_n]
        except Exception:
            logger.exception("LLM recipe generation fallback failed")

    # ── Category / meal-type filter ─────────────────────────────────────
    if request.category and merged:
        _CATEGORY_KEYWORDS: dict[str, set[str]] = {
            "breakfast": {"pancake", "waffle", "omelette", "omelet", "french toast", "muffin",
                          "smoothie", "oatmeal", "cereal", "scramble", "breakfast", "granola",
                          "yogurt", "egg", "bagel", "hash brown", "frittata"},
            "lunch": {"sandwich", "wrap", "salad", "soup", "lunch", "bowl", "quesadilla",
                      "panini", "burrito", "flatbread"},
            "dinner": {"steak", "roast", "casserole", "pasta", "curry", "stir fry",
                       "stew", "lasagna", "risotto", "dinner", "chicken", "beef",
                       "pork", "salmon", "grilled"},
            "dessert": {"cake", "cookie", "brownie", "pie", "ice cream", "pudding",
                        "mousse", "fudge", "cheesecake", "tart", "cupcake", "dessert",
                        "chocolate", "caramel", "sweet"},
            "appetizer": {"dip", "bruschetta", "crostini", "appetizer", "bite", "slider",
                          "stuffed", "spring roll", "hummus", "guacamole", "nachos"},
            "snack": {"snack", "bar", "trail mix", "popcorn", "chip", "cracker",
                      "energy ball", "granola bar", "nuts"},
        }
        cat_lower = request.category.lower()
        keywords = _CATEGORY_KEYWORDS.get(cat_lower, set())
        if keywords:
            filtered = [
                r for r in merged
                if any(kw in r["title"].lower() for kw in keywords)
                or any(kw in " ".join(r.get("all_ingredients", [])).lower() for kw in keywords)
            ]
            if filtered:
                merged = filtered

    if not merged:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recipes found for the given ingredients.",
        )

    # Assign final ranks
    for i, r in enumerate(merged):
        r["rank"] = i + 1

    logger.info(
        f"suggest_recipes: ingredients={request.ingredients} → "
        f"{len(local_results)} local, {len(external_results)} external "
        f"→ {len(merged)} merged (cuisine={request.cuisine})"
    )
    return merged


@app.get(
    "/substitute",
    response_model=SubstituteResponse,
    status_code=status.HTTP_200_OK,
    tags=["substitution"],
    summary="Get possible substitutes for an ingredient",
)
async def substitute(
    ingredient: str = Query(..., description="Ingredient to substitute", example="butter"),
    context: Optional[str] = Query(None, description="Usage context (e.g. baking)", example="baking"),
    hybrid: bool = Query(False, description="Use hybrid substitution (direct + cooccurrence)", example=False),
    top_k: int = Query(5, description="Number of substitutes to return", example=5),
):
    """
    Query Neo4j for direct and/or hybrid substitutes.

    - ingredient: required ingredient name  
    - context: optional use-case filter  
    - hybrid: if true, merges direct + co-occurrence methods  
    - top_k: how many substitutes to return  
    """
    try:
        raw_subs = await asyncio.to_thread(
            get_hybrid_substitutes,
            ingredient,
            context,
            top_k,
            use_hybrid=hybrid,
        )
    except Exception:
        logger.error("Substitution lookup failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve substitutes",
        )

    return SubstituteResponse(
        ingredient=ingredient,
        context=context,
        hybrid=hybrid,
        substitutes=raw_subs,
    )


# ——— CSV Fallback Data (for when Neo4j is empty) ———
_csv_paths = DataPaths()
_recipes_by_title: dict[str, dict] = {}
_ingredients_by_recipe_id: dict[str, list[str]] = defaultdict(list)

def _load_csv_recipes():
    """Load recipe data from CSV files as fallback for Neo4j."""
    global _recipes_by_title, _ingredients_by_recipe_id
    try:
        # Load ingredients
        with open(_csv_paths.recipe_ingredients, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                _ingredients_by_recipe_id[row["recipe_id"]].append(row["ingredient"])

        # Load recipes
        with open(_csv_paths.recipes, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                title_lower = row["title"].strip().lower()
                _recipes_by_title[title_lower] = {
                    "recipe_id": row["recipe_id"],
                    "title": row["title"],
                    "directions": row.get("directions", "[]"),
                    "link": row.get("link", ""),
                    "source": row.get("source", ""),
                }
        logger.info(f"📚 Loaded {len(_recipes_by_title)} recipes from CSV fallback")
    except Exception:
        logger.warning("Could not load CSV recipe fallback data", exc_info=True)

_load_csv_recipes()


def _get_recipe_from_sqlite(title: str) -> Optional[dict]:
    """Fetch recipe details from optimized SQLite DB."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Try exact match first
            cursor.execute("SELECT title, ingredients, directions, ner FROM recipes WHERE title = ?", (title,))
            row = cursor.fetchone()
            
            # If not found, try case-insensitive
            if not row:
                cursor.execute("SELECT title, ingredients, directions, ner FROM recipes WHERE title = ? COLLATE NOCASE", (title,))
                row = cursor.fetchone()
            
            if row:
                db_title, raw_ings, raw_dirs, ner = row
                
                # Parse ingredients (try ner first as it is cleaner)
                # If ner is None or empty, fallback to raw ingredients
                ingredients_list = []
                if ner:
                    try:
                        ingredients_list = literal_eval(ner)
                    except:
                        pass
                
                if not ingredients_list and raw_ings:
                    try:
                        ingredients_list = literal_eval(raw_ings)
                    except:
                        pass
                    
                # Parse directions
                directions_list = []
                if raw_dirs:
                    try:
                        parsed = literal_eval(raw_dirs)
                        if isinstance(parsed, list):
                            directions_list = parsed
                        else:
                            directions_list = [str(parsed)]
                    except:
                        directions_list = [str(raw_dirs)]
                    
                return {
                   "title": db_title,
                   "ingredients": ingredients_list,
                   "directions": directions_list,
                   "link": "",
                   "source": "SQLiteDB"
                }
    except Exception as e:
        logger.warning(f"SQLite lookup failed for {title}: {e}")
    return None


@app.get(
    "/recipes/{recipe_title}",
    response_model=RecipeDetails,
    status_code=status.HTTP_200_OK,
    summary="Fetch full recipe details by title",
    tags=["recipes"],
)
async def get_recipe_details(
    recipe_title: str = Path(
        ...,
        description="Exact recipe title (case-insensitive)",
        example="Marinated Flank Steak Recipe",
    )
):
    """
    Returns detailed recipe data. Tries Neo4j first, falls back to CSV.
    """
    # 1) Try SQLite first (SSOT)
    record = _get_recipe_from_sqlite(recipe_title)
    
    # 2) Try Neo4j if not found
    if not record:
        record = await asyncio.to_thread(fetch_recipe_details, recipe_title)

    # 3) Fall back to CSV
    if not record:
        csv_record = _recipes_by_title.get(recipe_title.strip().lower())
        if csv_record:
            recipe_id = csv_record["recipe_id"]
            ings = _ingredients_by_recipe_id.get(recipe_id, [])
            raw_dirs = csv_record["directions"]
            if isinstance(raw_dirs, str):
                try:
                    raw_dirs = literal_eval(raw_dirs)
                except Exception:
                    raw_dirs = [raw_dirs]
            # dedupe ingredients (plural aware)
            seen_keys = set()
            unique_ings = []
            for ing in ings:
                clean = ing.lower().strip()
                # Normalize plurals (simple heuristic)
                if clean.endswith('s') and len(clean) > 3:
                    key = clean[:-1]
                else:
                    key = clean
                
                if key not in seen_keys:
                    unique_ings.append(ing)
                    seen_keys.add(key)
                    # Also block the plural/singular form
                    if clean.endswith('s'): seen_keys.add(clean)
                    else: seen_keys.add(clean + 's')
            return RecipeDetails(
                title=csv_record["title"],
                directions=raw_dirs if isinstance(raw_dirs, list) else [raw_dirs],
                link=csv_record.get("link", ""),
                source=csv_record.get("source", ""),
                ingredients=unique_ings,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe '{recipe_title}' not found."
        )

    # Parse directions from Neo4j record
    raw_dirs = record.get("directions")
    if raw_dirs is None:
        raw_dirs = ["Directions not available."]
    elif isinstance(raw_dirs, str):
        try:
            raw_dirs = literal_eval(raw_dirs)
        except Exception:
            raw_dirs = [raw_dirs]
    elif not isinstance(raw_dirs, list):
         raw_dirs = [str(raw_dirs)]

    # Parse & dedupe ingredients (plural aware)
    raw_ings = record.get("ingredients", []) or []
    seen_keys = set()
    unique_ings: list[str] = []
    for ing in raw_ings:
        clean = ing.lower().strip()
        if clean.endswith('s') and len(clean) > 3:
            key = clean[:-1]
        else:
            key = clean

        if key not in seen_keys:
            unique_ings.append(ing)
            seen_keys.add(key)
            if clean.endswith('s'): seen_keys.add(clean)
            else: seen_keys.add(clean + 's')

    return RecipeDetails(
        title=record.get("title", ""),
        directions=raw_dirs,
        link=record.get("link", ""),
        source=record.get("source", ""),
        ingredients=unique_ings,
    )


@app.post(
    "/recipes/{recipe_title}/substitutions",
    response_model=PantrySubstitutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pantry-aware ingredient substitutions for a recipe",
    tags=["substitution"],
)
async def get_recipe_substitutions(
    recipe_title: str = Path(
        ...,
        description="Recipe title to analyze",
        example="Fried Rice",
    ),
    request: PantrySubstitutionRequest = ...,
):
    """
    Compare a recipe's ingredients against the user's pantry.

    Returns:
    - Which ingredients the user already HAS
    - Which ingredients are MISSING
    - For each missing ingredient: substitutes from the user's pantry + other options
    """
    # 1) Get recipe ingredients (reuse existing detail logic)
    # Try Neo4j first, gracefully fall through to CSV if Neo4j is down
    record = None
    try:
        record = _get_recipe_from_sqlite(recipe_title)
        if not record:
            record = await asyncio.to_thread(fetch_recipe_details, recipe_title)
    except Exception:
        logger.warning("Neo4j/SQLite unavailable for substitution lookup, falling back to CSV")

    recipe_ingredients = []
    if record:
        raw_ings = record.get("ingredients", []) or []
        seen_keys = set()
        for ing in raw_ings:
            clean = ing.lower().strip()
            if clean.endswith('s') and len(clean) > 3:
                key = clean[:-1]
            else:
                key = clean
            
            if ing and key not in seen_keys:
                recipe_ingredients.append(ing)
                seen_keys.add(key)
                if clean.endswith('s'): seen_keys.add(clean)
                else: seen_keys.add(clean + 's')
    else:
        # CSV fallback
        csv_record = _recipes_by_title.get(recipe_title.strip().lower())
        if csv_record:
            recipe_id = csv_record["recipe_id"]
            ings = _ingredients_by_recipe_id.get(recipe_id, [])
            seen_keys = set()
            for ing in ings:
                clean = ing.lower().strip()
                if clean.endswith('s') and len(clean) > 3:
                    key = clean[:-1]
                else:
                    key = clean

                if key not in seen_keys:
                    recipe_ingredients.append(ing)
                    seen_keys.add(key)
                    if clean.endswith('s'): seen_keys.add(clean)
                    else: seen_keys.add(clean + 's')

    if not recipe_ingredients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe '{recipe_title}' not found or has no ingredients.",
        )

    # 2) Run pantry-aware substitution
    try:
        result = await asyncio.to_thread(
            get_pantry_substitutions,
            recipe_ingredients,
            request.pantry,
        )
    except Exception:
        logger.exception("Failed to compute pantry substitutions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not compute substitutions",
        )

    return PantrySubstitutionResponse(
        recipe_title=recipe_title,
        **result,
    )
