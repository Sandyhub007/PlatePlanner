import asyncio
import csv
import logging
from collections import defaultdict
from typing import List, Optional
from ast import literal_eval

from fastapi import FastAPI, HTTPException, Query, status, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.services.neo4j_service import get_hybrid_substitutes, recipe_details as fetch_recipe_details
from src.services.substitution_service import get_pantry_substitutions
from src.utils.recipesuggestionmodel import suggest_recipes, metadata_df
from src.api.routers import auth, users, meal_plans, shopping_lists, nutrition
from src.database.session import engine, Base
from src.database.schema_guards import ensure_phase_two_schema, ensure_phase_three_schema
from src.config.paths import DataPaths

# ——— Database Initialization ———
Base.metadata.create_all(bind=engine)
ensure_phase_two_schema()
ensure_phase_three_schema()  # Phase 3: Shopping Lists

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
    ],
)

# ——— CORS ———
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # <-- lock this down in production
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

# ——— Logging ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("plate_planner")


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
    
    # New dietary filters
    is_vegan: bool = Field(False, description="Filter for vegan recipes")
    is_vegetarian: bool = Field(False, description="Filter for vegetarian recipes")
    is_gluten_free: bool = Field(False, description="Filter for gluten-free recipes")
    is_dairy_free: bool = Field(False, description="Filter for dairy-free recipes")

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
    tags: Optional[dict] = None  # Return dietary tags


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


# ——— Endpoints ———
@app.get("/", tags=["health"], summary="Health check")
async def root() -> dict:
    return {"message": "Plate Planner API is running."}


@app.post(
    "/suggest_recipes",
    response_model=List[RecipeResult],
    status_code=status.HTTP_200_OK,
    summary="Suggest recipes (only overlapping ingredients returned)",
    tags=["recipes"],
)
async def suggest_recipes_endpoint(request: RecipeRequest):
    try:
        results = await asyncio.to_thread(
            suggest_recipes,
            request.ingredients,
            request.top_n,
            request.rerank_weight,
            500, # raw_k
            2, # min_overlap
            request.is_vegan,
            request.is_vegetarian,
            request.is_gluten_free,
            request.is_dairy_free
        )
    except Exception:
        logger.exception("Failed to suggest recipes")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate recipe suggestions",
        )

    return results


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
    # 1) Try Neo4j first
    record = await asyncio.to_thread(fetch_recipe_details, recipe_title)

    # 2) Fall back to CSV
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
            # dedupe ingredients
            seen = set()
            unique_ings = []
            for ing in ings:
                if ing not in seen:
                    unique_ings.append(ing)
                    seen.add(ing)
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

    # Parse & dedupe ingredients
    raw_ings = record.get("ingredients", []) or []
    seen = set()
    unique_ings: list[str] = []
    for ing in raw_ings:
        if ing not in seen:
            unique_ings.append(ing)
            seen.add(ing)

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
        record = await asyncio.to_thread(fetch_recipe_details, recipe_title)
    except Exception:
        logger.warning("Neo4j unavailable for substitution lookup, falling back to CSV")

    recipe_ingredients = []
    if record:
        raw_ings = record.get("ingredients", []) or []
        seen = set()
        for ing in raw_ings:
            if ing and ing not in seen:
                recipe_ingredients.append(ing)
                seen.add(ing)
    else:
        # CSV fallback
        csv_record = _recipes_by_title.get(recipe_title.strip().lower())
        if csv_record:
            recipe_id = csv_record["recipe_id"]
            ings = _ingredients_by_recipe_id.get(recipe_id, [])
            seen = set()
            for ing in ings:
                if ing not in seen:
                    recipe_ingredients.append(ing)
                    seen.add(ing)

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
