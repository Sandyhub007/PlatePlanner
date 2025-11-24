from __future__ import annotations

import csv
import random
from ast import literal_eval
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Sequence

import faiss
import numpy as np
from sqlalchemy.orm import Session, selectinload

from src.config.paths import DataPaths
from src.database import models
from src.schemas.meal_plan import MealPlanPreferencesOverride
from src.utils.recipesuggestionmodel import metadata_df, model as embedding_model, index as faiss_index

MEAL_SPLITS: Dict[str, float] = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.40}
DEFAULT_CALORIE_TARGET = 2000
DEFAULT_SERVINGS = 1
CANDIDATE_POOL_TARGET = 420
MIN_CANDIDATE_POOL = 90

PROTEIN_KEYWORDS = {
    "chicken",
    "beef",
    "turkey",
    "pork",
    "egg",
    "salmon",
    "tuna",
    "bean",
    "lentil",
    "tofu",
    "yogurt",
    "shrimp",
    "steak",
    "ham",
}
CARB_KEYWORDS = {
    "rice",
    "pasta",
    "noodle",
    "bread",
    "tortilla",
    "potato",
    "quinoa",
    "oat",
    "flour",
    "spaghetti",
    "macaroni",
    "corn",
}
FAT_KEYWORDS = {
    "butter",
    "oil",
    "olive",
    "avocado",
    "bacon",
    "cream",
    "cheese",
    "nut",
    "peanut",
    "almond",
    "walnut",
    "coconut",
    "sesame",
}

DIETARY_BLOCKLIST: Dict[str, set[str]] = {
    "vegan": {"chicken", "beef", "pork", "fish", "egg", "milk", "cheese", "honey", "butter", "yogurt"},
    "vegetarian": {"chicken", "beef", "pork", "fish", "shrimp", "bacon", "ham"},
    "gluten-free": {"wheat", "barley", "rye", "pasta", "bread", "flour"},
    "keto": {"sugar", "rice", "pasta", "bread", "potato", "corn", "honey"},
}

CUISINE_KEYWORDS: Dict[str, set[str]] = {
    "mexican": {"taco", "enchilada", "quesadilla", "jalapeno", "salsa", "chipotle"},
    "italian": {"pasta", "lasagna", "parm", "risotto", "gnocchi", "marinara"},
    "indian": {"curry", "masala", "paneer", "tikka", "dal", "garam"},
    "asian": {"soy", "ginger", "sesame", "teriyaki", "noodle", "kimchi"},
    "mediterranean": {"feta", "olive", "tzatziki", "hummus", "oregano"},
    "american": {"burger", "barbecue", "bbq", "casserole", "mac"},
}

METADATA_TITLE_LOOKUP: List[str] = [
    str(title).strip().lower()
    for title in metadata_df["title"].fillna("").tolist()
]


@dataclass(frozen=True)
class NutritionEstimate:
    calories: int
    protein: int
    carbs: int
    fat: int


@dataclass(frozen=True)
class RecipeRecord:
    recipe_id: str
    title: str
    normalized_title: str
    ingredients: tuple[str, ...]
    ingredient_set: frozenset[str]
    cuisine_tags: frozenset[str]
    nutrition: NutritionEstimate
    estimated_cost: float
    prep_time_minutes: int


@dataclass(frozen=True)
class PreferenceProfile:
    dietary_restrictions: List[str]
    allergies: List[str]
    cuisine_preferences: List[str]
    calorie_target: Optional[int]
    protein_target: Optional[int]
    carb_target: Optional[int]
    fat_target: Optional[int]
    cooking_time_max: Optional[int]
    budget_per_week: Optional[float]
    people_count: int


@dataclass(frozen=True)
class MealSlot:
    day_index: int
    meal_type: str
    calorie_target: int
    per_meal_budget: Optional[float]
    max_prep_time: Optional[int]


@dataclass(frozen=True)
class PlanAssignment:
    day_of_week: int
    meal_type: str
    recipe: RecipeRecord
    servings: int


@dataclass(frozen=True)
class GeneratedPlan:
    assignments: List[PlanAssignment]
    total_calories: int
    total_protein: int
    total_carbs: int
    total_fat: int
    total_cost: float


def _normalize_value(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _contains_keyword(text: str, keywords: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _has_any_keyword(parts: Iterable[str], keywords: Iterable[str]) -> bool:
    kw_list = list(keywords)
    if not kw_list:
        return False
    for part in parts:
        lowered = part.lower()
        for keyword in kw_list:
            if keyword in lowered:
                return True
    return False


def _extract_ingredients(raw_value: str) -> List[str]:
    raw_value = (raw_value or "").strip()
    if not raw_value:
        return []
    candidates: List[str]
    if raw_value.startswith("["):
        try:
            parsed = literal_eval(raw_value)
            if isinstance(parsed, (list, tuple)):
                candidates = [str(item) for item in parsed]
            else:
                candidates = [raw_value]
        except (ValueError, SyntaxError):
            candidates = [raw_value]
    else:
        candidates = raw_value.split(",")
    seen: set[str] = set()
    cleaned: List[str] = []
    for item in candidates:
        normalized = _normalize_value(item)
        if normalized and normalized not in seen:
            cleaned.append(normalized)
            seen.add(normalized)
    return cleaned


def _parse_directions(raw_value: Optional[str]) -> int:
    if not raw_value:
        return 4
    try:
        parsed = literal_eval(raw_value)
        if isinstance(parsed, (list, tuple)):
            return max(len(parsed), 3)
    except (ValueError, SyntaxError):
        return 4
    return 4


def _estimate_prep_time(ingredients: Sequence[str], raw_directions: Optional[str]) -> int:
    steps = _parse_directions(raw_directions)
    estimate = 8 + len(ingredients) * 2 + steps * 3
    return max(10, min(90, estimate))


def _estimate_nutrition(ingredients: Sequence[str]) -> NutritionEstimate:
    protein_hits = sum(1 for ing in ingredients if _contains_keyword(ing, PROTEIN_KEYWORDS))
    carb_hits = sum(1 for ing in ingredients if _contains_keyword(ing, CARB_KEYWORDS))
    fat_hits = sum(1 for ing in ingredients if _contains_keyword(ing, FAT_KEYWORDS))
    base = 120 + len(ingredients) * 30
    calories = min(900, base + protein_hits * 35 + carb_hits * 25 + fat_hits * 45)
    protein = max(8, protein_hits * 12)
    carbs = max(12, carb_hits * 15)
    fat = max(8, fat_hits * 10)
    return NutritionEstimate(calories=calories, protein=protein, carbs=carbs, fat=fat)


def _estimate_cost(ingredients: Sequence[str], nutrition: NutritionEstimate) -> float:
    base = 2.0 + len(ingredients) * 0.65
    protein_bonus = nutrition.protein * 0.05
    fat_bonus = nutrition.fat * 0.03
    return base + protein_bonus + fat_bonus


def _infer_cuisines(title: str, ingredients: Sequence[str]) -> set[str]:
    tags: set[str] = set()
    title_lower = title.lower()
    combined = list(ingredients) + [title_lower]
    for cuisine, keywords in CUISINE_KEYWORDS.items():
        if _has_any_keyword(combined, keywords):
            tags.add(cuisine)
    return tags


def _violates_diet(record: RecipeRecord, restrictions: Iterable[str]) -> bool:
    for restriction in restrictions:
        banned = DIETARY_BLOCKLIST.get(restriction)
        if banned and _has_any_keyword(record.ingredient_set, banned):
            return True
    return False


def _violates_allergies(record: RecipeRecord, allergies: Iterable[str]) -> bool:
    lowered = [allergy.lower() for allergy in allergies]
    return _has_any_keyword(record.ingredient_set, lowered)


def _matches_cuisine(record: RecipeRecord, preferences: Iterable[str]) -> bool:
    wanted = {pref.lower() for pref in preferences if pref}
    if not wanted:
        return True
    if record.cuisine_tags & wanted:
        return True
    title = record.title.lower()
    return any(pref in title for pref in wanted)


@lru_cache(maxsize=1)
def _load_recipe_library() -> tuple[List[RecipeRecord], Dict[str, RecipeRecord]]:
    paths = DataPaths()
    metadata_rows = [
        (str(row.title).strip(), str(row.NER) if row.NER is not None else "")
        for row in metadata_df.itertuples(index=False)
    ]
    metadata_titles = {title.lower() for title, _ in metadata_rows if title}

    title_to_recipe_row: Dict[str, dict] = {}
    with open(paths.recipes, newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            title_key = _normalize_value(row.get("title"))
            if title_key and title_key in metadata_titles and title_key not in title_to_recipe_row:
                title_to_recipe_row[title_key] = row

    recipe_ids = {row["recipe_id"] for row in title_to_recipe_row.values()}
    ingredient_map: Dict[str, List[str]] = defaultdict(list)
    with open(paths.recipe_ingredients, newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            recipe_id = row.get("recipe_id")
            if recipe_id in recipe_ids:
                normalized = _normalize_value(row.get("ingredient"))
                if normalized:
                    ingredient_map[recipe_id].append(normalized)

    records: Dict[str, RecipeRecord] = {}
    for title, ner_values in metadata_rows:
        key = title.lower()
        recipe_row = title_to_recipe_row.get(key)
        if not recipe_row:
            continue
        recipe_id = recipe_row["recipe_id"]
        ingredients = _extract_ingredients(ner_values)
        if not ingredients:
            ingredients = ingredient_map.get(recipe_id, [])
        if len(ingredients) < 3:
            continue
        deduped = tuple(dict.fromkeys(ingredients))
        nutrition = _estimate_nutrition(deduped)
        prep_time = _estimate_prep_time(deduped, recipe_row.get("directions"))
        cost = _estimate_cost(deduped, nutrition)
        cuisine_tags = _infer_cuisines(title, deduped)
        records[key] = RecipeRecord(
            recipe_id=str(recipe_id),
            title=title,
            normalized_title=key,
            ingredients=deduped,
            ingredient_set=frozenset(deduped),
            cuisine_tags=frozenset(cuisine_tags),
            nutrition=nutrition,
            estimated_cost=round(cost, 2),
            prep_time_minutes=prep_time,
        )

    record_list = list(records.values())
    record_list.sort(key=lambda rec: rec.title)
    return record_list, records


class MealPlanEngine:
    def __init__(self) -> None:
        self.library, self.title_lookup = _load_recipe_library()
        self.meal_types = list(MEAL_SPLITS.keys())

    def build_plan(self, profile: PreferenceProfile, week_start: date) -> GeneratedPlan:
        candidate_pool = self._build_candidate_pool(profile)
        if not candidate_pool:
            raise ValueError("Unable to find recipes that satisfy the given preferences")

        slots = self._build_slots(profile)
        per_meal_budget = slots[0].per_meal_budget if slots else None
        used_recent = deque(maxlen=5)
        assignments: List[PlanAssignment] = []
        totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
        total_cost = 0.0
        remaining_budget = profile.budget_per_week
        servings = profile.people_count

        for slot in slots:
            recipe = self._pick_recipe(candidate_pool, slot, profile, used_recent, remaining_budget)
            assignments.append(PlanAssignment(day_of_week=slot.day_index, meal_type=slot.meal_type, recipe=recipe, servings=servings))
            totals["calories"] += recipe.nutrition.calories * servings
            totals["protein"] += recipe.nutrition.protein * servings
            totals["carbs"] += recipe.nutrition.carbs * servings
            totals["fat"] += recipe.nutrition.fat * servings
            meal_cost = recipe.estimated_cost * servings
            total_cost += meal_cost
            if remaining_budget is not None:
                remaining_budget -= meal_cost

        return GeneratedPlan(
            assignments=assignments,
            total_calories=totals["calories"],
            total_protein=totals["protein"],
            total_carbs=totals["carbs"],
            total_fat=totals["fat"],
            total_cost=round(total_cost, 2),
        )

    def _build_candidate_pool(self, profile: PreferenceProfile) -> List[RecipeRecord]:
        preference_text = self._preference_text(profile)
        query_vec = embedding_model.encode([preference_text])
        query_vec = np.array(query_vec).astype("float32")
        faiss.normalize_L2(query_vec)

        pool_size = min(CANDIDATE_POOL_TARGET, faiss_index.ntotal)
        _, indices = faiss_index.search(query_vec, pool_size)

        seen_ids: set[str] = set()
        candidates: List[RecipeRecord] = []
        for idx in indices[0]:
            if idx < 0 or idx >= len(METADATA_TITLE_LOOKUP):
                continue
            title_key = METADATA_TITLE_LOOKUP[idx]
            record = self.title_lookup.get(title_key)
            if record and record.recipe_id not in seen_ids:
                candidates.append(record)
                seen_ids.add(record.recipe_id)
        filtered = self._filter_by_preferences(candidates, profile)
        if len(filtered) < MIN_CANDIDATE_POOL:
            filtered.extend(self._fallback_candidates(profile, MIN_CANDIDATE_POOL - len(filtered)))
        return filtered

    def _filter_by_preferences(self, records: List[RecipeRecord], profile: PreferenceProfile) -> List[RecipeRecord]:
        results: List[RecipeRecord] = []
        for record in records:
            if _violates_diet(record, profile.dietary_restrictions):
                continue
            if _violates_allergies(record, profile.allergies):
                continue
            if not _matches_cuisine(record, profile.cuisine_preferences):
                continue
            results.append(record)
        return results

    def _fallback_candidates(self, profile: PreferenceProfile, needed: int) -> List[RecipeRecord]:
        filtered = [
            record
            for record in self.library
            if not _violates_diet(record, profile.dietary_restrictions)
            and not _violates_allergies(record, profile.allergies)
        ]
        random.shuffle(filtered)
        if needed <= 0:
            return filtered
        return filtered[:needed] if filtered else []

    def _build_slots(self, profile: PreferenceProfile) -> List[MealSlot]:
        slots: List[MealSlot] = []
        total_meals = 7 * len(self.meal_types)
        per_meal_budget = None
        if profile.budget_per_week:
            per_meal_budget = profile.budget_per_week / total_meals
        calorie_target = profile.calorie_target or DEFAULT_CALORIE_TARGET
        for day in range(7):
            for meal_type, ratio in MEAL_SPLITS.items():
                slots.append(
                    MealSlot(
                        day_index=day,
                        meal_type=meal_type,
                        calorie_target=max(250, int(calorie_target * ratio)),
                        per_meal_budget=per_meal_budget,
                        max_prep_time=profile.cooking_time_max,
                    )
                )
        return slots

    def _pick_recipe(
        self,
        candidates: List[RecipeRecord],
        slot: MealSlot,
        profile: PreferenceProfile,
        used_recent: deque[str],
        remaining_budget: Optional[float],
    ) -> RecipeRecord:
        best: Optional[RecipeRecord] = None
        best_score = float("inf")
        for record in candidates:
            if slot.max_prep_time and record.prep_time_minutes > slot.max_prep_time:
                continue
            if slot.per_meal_budget and record.estimated_cost > slot.per_meal_budget * 1.4:
                continue
            repeat_penalty = 200 if record.recipe_id in used_recent else 0
            calorie_penalty = abs(record.nutrition.calories - slot.calorie_target)
            budget_penalty = 0.0
            if remaining_budget is not None:
                projected = remaining_budget - (record.estimated_cost * profile.people_count)
                if slot.per_meal_budget:
                    deficit = projected - (-slot.per_meal_budget)
                    if deficit < 0:
                        budget_penalty = abs(deficit) * 10
            score = calorie_penalty + repeat_penalty + budget_penalty
            if best is None or score < best_score:
                best = record
                best_score = score
        if best is None:
            best = random.choice(candidates)
        used_recent.append(best.recipe_id)
        return best

    def _preference_text(self, profile: PreferenceProfile) -> str:
        tokens: List[str] = []
        tokens.extend(profile.cuisine_preferences)
        tokens.extend(f"{restriction} friendly" for restriction in profile.dietary_restrictions)
        if profile.cooking_time_max:
            tokens.append("quick" if profile.cooking_time_max <= 30 else "slow cooked")
        if profile.budget_per_week:
            tokens.append("budget conscious")
        if profile.people_count and profile.people_count > 2:
            tokens.append("family style")
        return " ".join(tokens) or "balanced healthy meal plan"


def _build_preference_profile(
    user_preferences: Optional[models.UserPreferences],
    override: Optional[MealPlanPreferencesOverride],
) -> PreferenceProfile:
    base = {
        "dietary_restrictions": list((user_preferences.dietary_restrictions or []) if user_preferences else []),
        "allergies": list((user_preferences.allergies or []) if user_preferences else []),
        "cuisine_preferences": list((user_preferences.cuisine_preferences or []) if user_preferences else []),
        "calorie_target": user_preferences.calorie_target if user_preferences else None,
        "protein_target": user_preferences.protein_target if user_preferences else None,
        "carb_target": user_preferences.carb_target if user_preferences else None,
        "fat_target": user_preferences.fat_target if user_preferences else None,
        "cooking_time_max": user_preferences.cooking_time_max if user_preferences else None,
        "budget_per_week": user_preferences.budget_per_week if user_preferences else None,
        "people_count": user_preferences.people_count if user_preferences and user_preferences.people_count else DEFAULT_SERVINGS,
    }
    if override:
        override_data = override.model_dump(exclude_none=True)
        for key, value in override_data.items():
            base[key] = value
    base["dietary_restrictions"] = [value.lower() for value in base.get("dietary_restrictions", [])]
    base["allergies"] = [value.lower() for value in base.get("allergies", [])]
    base["cuisine_preferences"] = [value.lower() for value in base.get("cuisine_preferences", [])]
    base["people_count"] = max(1, int(base.get("people_count") or DEFAULT_SERVINGS))
    return PreferenceProfile(**base)


def _coerce_week_start(value: date | str) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


_ENGINE = MealPlanEngine()


def generate_meal_plan(
    db: Session,
    user_id: str,
    week_start_date: date | str,
    preferences_override: Optional[MealPlanPreferencesOverride] = None,
) -> models.MealPlan:
    week_start = _coerce_week_start(week_start_date)
    user = (
        db.query(models.User)
        .options(selectinload(models.User.preferences))
        .filter(models.User.id == user_id)
        .first()
    )
    if not user:
        raise ValueError("User not found")

    profile = _build_preference_profile(user.preferences, preferences_override)
    plan = _ENGINE.build_plan(profile, week_start)

    meal_plan = models.MealPlan(
        user_id=user_id,
        week_start_date=week_start,
        week_end_date=week_start + timedelta(days=6),
        status="draft",
        total_calories=plan.total_calories,
        total_protein=plan.total_protein,
        total_carbs=plan.total_carbs,
        total_fat=plan.total_fat,
        total_estimated_cost=plan.total_cost,
    )
    db.add(meal_plan)
    db.flush()

    for assignment in plan.assignments:
        record = assignment.recipe
        db.add(
            models.MealPlanItem(
                plan_id=meal_plan.id,
                day_of_week=assignment.day_of_week,
                meal_type=assignment.meal_type,
                recipe_id=record.recipe_id,
                recipe_title=record.title,
                servings=assignment.servings,
                calories=record.nutrition.calories,
                protein=record.nutrition.protein,
                carbs=record.nutrition.carbs,
                fat=record.nutrition.fat,
                estimated_cost=round(record.estimated_cost * assignment.servings, 2),
                prep_time_minutes=record.prep_time_minutes,
            )
        )

    db.commit()
    return get_meal_plan(db, meal_plan.id)


def get_meal_plan(db: Session, plan_id: str) -> Optional[models.MealPlan]:
    return (
        db.query(models.MealPlan)
        .options(selectinload(models.MealPlan.items))
        .filter(models.MealPlan.id == plan_id)
        .first()
    )


def get_user_meal_plans(db: Session, user_id: str) -> List[models.MealPlan]:
    return (
        db.query(models.MealPlan)
        .options(selectinload(models.MealPlan.items))
        .filter(models.MealPlan.user_id == user_id)
        .order_by(models.MealPlan.week_start_date.desc())
        .all()
    )
