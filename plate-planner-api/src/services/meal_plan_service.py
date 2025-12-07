from __future__ import annotations

import csv
import random
from ast import literal_eval
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta
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
CALORIE_TOLERANCE = 0.05

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


def _load_user_with_preferences(db: Session, user_id: str) -> Optional[models.User]:
    return (
        db.query(models.User)
        .options(selectinload(models.User.preferences))
        .filter(models.User.id == user_id)
        .first()
    )


def _per_meal_budget(profile: PreferenceProfile) -> Optional[float]:
    if not profile.budget_per_week:
        return None
    meals_per_week = 7 * len(MEAL_SPLITS)
    if meals_per_week == 0:
        return None
    return profile.budget_per_week / meals_per_week


def _slot_for_item(profile: PreferenceProfile, item: models.MealPlanItem) -> MealSlot:
    ratio = MEAL_SPLITS.get(item.meal_type, 1 / max(len(MEAL_SPLITS), 1))
    calorie_target = profile.calorie_target or DEFAULT_CALORIE_TARGET
    return MealSlot(
        day_index=item.day_of_week,
        meal_type=item.meal_type,
        calorie_target=max(250, int(calorie_target * ratio)),
        per_meal_budget=_per_meal_budget(profile),
        max_prep_time=profile.cooking_time_max,
    )


def _recalculate_plan_totals(plan: models.MealPlan) -> None:
    plan.total_calories = sum(item.calories or 0 for item in plan.items)
    plan.total_protein = sum(item.protein or 0 for item in plan.items)
    plan.total_carbs = sum(item.carbs or 0 for item in plan.items)
    plan.total_fat = sum(item.fat or 0 for item in plan.items)
    plan.total_estimated_cost = round(sum(item.estimated_cost or 0.0 for item in plan.items), 2)


def _aggregate_nutrition_totals(items: List[models.MealPlanItem]) -> Dict[str, int]:
    return {
        "calories": sum(item.calories or 0 for item in items),
        "protein": sum(item.protein or 0 for item in items),
        "carbs": sum(item.carbs or 0 for item in items),
        "fat": sum(item.fat or 0 for item in items),
    }


def _build_summary_payload(
    plan: models.MealPlan,
    *,
    include_meals: bool = True,
    serialize_dates: bool = False,
    include_plan_id: bool = True,
) -> dict:
    start_date = plan.week_start_date or date.today()
    end_date = plan.week_end_date or (start_date + timedelta(days=6))
    total_days = max(1, (end_date - start_date).days + 1)

    def _date_value(value: date) -> date | str:
        return value.isoformat() if serialize_dates else value

    daily: List[dict] = []
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    total_prep = 0
    total_meals = 0

    for day in range(total_days):
        day_items = [item for item in plan.items if item.day_of_week == day]
        day_totals = _aggregate_nutrition_totals(day_items)
        day_prep = sum(item.prep_time_minutes or 0 for item in day_items)
        for key in total:
            total[key] += day_totals[key]
        total_prep += day_prep
        total_meals += len(day_items)
        day_entry = {
            "day_index": day,
            "date": _date_value(start_date + timedelta(days=day)),
            "total": day_totals,
            "total_prep_time_minutes": day_prep,
        }
        if include_meals:
            day_entry["meals"] = day_items
        daily.append(day_entry)

    average_prep = total_prep / total_meals if total_meals else 0.0

    summary = {
        "week_start_date": _date_value(start_date),
        "week_end_date": _date_value(end_date),
        "total": total,
        "daily": daily,
        "total_estimated_cost": plan.total_estimated_cost,
        "average_prep_time_minutes": round(average_prep, 2),
    }
    if include_plan_id:
        summary["plan_id"] = plan.id if not serialize_dates else str(plan.id)
    return summary



def _ensure_summary_snapshot(plan: models.MealPlan, refresh: bool = False) -> dict:
    if refresh or not plan.summary_snapshot:
        plan.summary_snapshot = _build_summary_payload(
            plan,
            include_meals=False,
            serialize_dates=True,
            include_plan_id=False,
        )
        plan.summary_generated_at = datetime.utcnow()
    return plan.summary_snapshot or {}


def _hydrate_summary_response(plan: models.MealPlan, snapshot: dict) -> dict:
    data = deepcopy(snapshot) if snapshot else {}
    data.setdefault("week_start_date", plan.week_start_date or date.today())
    data.setdefault("week_end_date", plan.week_end_date or (plan.week_start_date or date.today()) + timedelta(days=6))
    data.setdefault("daily", [])
    data.setdefault("total", {"calories": 0, "protein": 0, "carbs": 0, "fat": 0})
    data.setdefault("total_estimated_cost", plan.total_estimated_cost)
    data.setdefault("average_prep_time_minutes", 0.0)

    def _coerce_date(value):
        if isinstance(value, str):
            return date.fromisoformat(value)
        return value

    data["week_start_date"] = _coerce_date(data.get("week_start_date"))
    data["week_end_date"] = _coerce_date(data.get("week_end_date"))

    meals_by_day: Dict[int, List[models.MealPlanItem]] = defaultdict(list)
    for item in plan.items:
        meals_by_day[item.day_of_week].append(item)

    for day_entry in data.get("daily", []):
        day_index = day_entry.get("day_index", 0)
        day_entry["date"] = _coerce_date(day_entry.get("date"))
        day_entry["meals"] = meals_by_day.get(day_index, [])

    data["plan_id"] = plan.id
    return data


def _refresh_plan_state(
    db: Session,
    plan: models.MealPlan,
    profile: PreferenceProfile,
    *,
    refresh_summary: bool = True,
) -> None:
    """Refresh validation and summary state for a meal plan."""
    issues = _run_validation_checks(plan, profile)
    plan.is_valid = not any(issue["severity"] == "error" for issue in issues)
    plan.validation_issues = issues
    plan.last_validated_at = datetime.utcnow()
    if refresh_summary:
        plan.summary_snapshot = _build_summary_payload(
            plan,
            include_meals=False,
            serialize_dates=True,
            include_plan_id=False,
        )
        plan.summary_generated_at = datetime.utcnow()
    db.add(plan)


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


@lru_cache(maxsize=1)
def _recipe_id_lookup() -> Dict[str, RecipeRecord]:
    record_list, _ = _load_recipe_library()
    return {record.recipe_id: record for record in record_list}


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
    user = _load_user_with_preferences(db, user_id)
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

    _refresh_plan_state(db, meal_plan, profile)
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


def list_meal_plan_alternatives(
    db: Session,
    user_id: str,
    plan_id: str,
    item_id: str,
    limit: int = 5,
    preferences_override: Optional[MealPlanPreferencesOverride] = None,
) -> List[dict]:
    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise ValueError("Meal plan not found")
    if str(plan.user_id) != str(user_id):
        raise ValueError("Not authorized to view this meal plan")
    target_item = next((item for item in plan.items if str(item.id) == str(item_id)), None)
    if not target_item:
        raise ValueError("Meal plan item not found")

    user = _load_user_with_preferences(db, user_id)
    if not user:
        raise ValueError("User not found")
    profile = _build_preference_profile(user.preferences, preferences_override)
    slot = _slot_for_item(profile, target_item)
    candidate_pool = _ENGINE._build_candidate_pool(profile)

    used_ids = {item.recipe_id for item in plan.items}
    alternatives: List[tuple[float, RecipeRecord]] = []
    for record in candidate_pool:
        if record.recipe_id in used_ids or record.recipe_id == target_item.recipe_id:
            continue
        if slot.max_prep_time and record.prep_time_minutes > slot.max_prep_time:
            continue
        if slot.per_meal_budget and record.estimated_cost > slot.per_meal_budget * 1.4:
            continue
        score = abs(record.nutrition.calories - slot.calorie_target)
        alternatives.append((score, record))
        if len(alternatives) >= limit * 8:
            break

    alternatives.sort(key=lambda pair: pair[0])
    top = [record for _, record in alternatives[:limit]]
    return [
        {
            "recipe_id": record.recipe_id,
            "title": record.title,
            "calories": record.nutrition.calories,
            "protein": record.nutrition.protein,
            "carbs": record.nutrition.carbs,
            "fat": record.nutrition.fat,
            "estimated_cost": record.estimated_cost,
            "prep_time_minutes": record.prep_time_minutes,
        }
        for record in top
    ]


def swap_meal_plan_item(
    db: Session,
    user_id: str,
    plan_id: str,
    item_id: str,
    new_recipe_id: str,
) -> models.MealPlan:
    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise ValueError("Meal plan not found")
    if str(plan.user_id) != str(user_id):
        raise ValueError("Not authorized to modify this meal plan")
    target_item = next((item for item in plan.items if str(item.id) == str(item_id)), None)
    if not target_item:
        raise ValueError("Meal plan item not found")

    recipe = _recipe_id_lookup().get(str(new_recipe_id))
    if not recipe:
        raise ValueError("Recipe not found in library")

    target_item.recipe_id = recipe.recipe_id
    target_item.recipe_title = recipe.title
    target_item.calories = recipe.nutrition.calories
    target_item.protein = recipe.nutrition.protein
    target_item.carbs = recipe.nutrition.carbs
    target_item.fat = recipe.nutrition.fat
    target_item.estimated_cost = round(recipe.estimated_cost * target_item.servings, 2)
    target_item.prep_time_minutes = recipe.prep_time_minutes

    db.add(target_item)
    _recalculate_plan_totals(plan)

    user = _load_user_with_preferences(db, user_id)
    if not user:
        raise ValueError("User not found")
    profile = _build_preference_profile(user.preferences, None)
    _refresh_plan_state(db, plan, profile)
    db.commit()
    return get_meal_plan(db, plan_id)


def regenerate_meal_plan_assignments(
    db: Session,
    user_id: str,
    plan_id: str,
    day_of_week: Optional[int] = None,
    preferences_override: Optional[MealPlanPreferencesOverride] = None,
) -> models.MealPlan:
    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise ValueError("Meal plan not found")
    if str(plan.user_id) != str(user_id):
        raise ValueError("Not authorized to modify this meal plan")
    if day_of_week is not None and (day_of_week < 0 or day_of_week > 6):
        raise ValueError("day_of_week must be between 0 and 6")

    user = _load_user_with_preferences(db, user_id)
    if not user:
        raise ValueError("User not found")
    profile = _build_preference_profile(user.preferences, preferences_override)
    new_plan = _ENGINE.build_plan(profile, plan.week_start_date)

    if day_of_week is None:
        db.query(models.MealPlanItem).filter(models.MealPlanItem.plan_id == plan.id).delete(synchronize_session=False)
        for assignment in new_plan.assignments:
            record = assignment.recipe
            db.add(
                models.MealPlanItem(
                    plan_id=plan.id,
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
        plan.total_calories = new_plan.total_calories
        plan.total_protein = new_plan.total_protein
        plan.total_carbs = new_plan.total_carbs
        plan.total_fat = new_plan.total_fat
        plan.total_estimated_cost = new_plan.total_cost
        db.add(plan)
    else:
        db.query(models.MealPlanItem).filter(
            models.MealPlanItem.plan_id == plan.id,
            models.MealPlanItem.day_of_week == day_of_week,
        ).delete(synchronize_session=False)
        replacements = [assignment for assignment in new_plan.assignments if assignment.day_of_week == day_of_week]
        for assignment in replacements:
            record = assignment.recipe
            db.add(
                models.MealPlanItem(
                    plan_id=plan.id,
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
    db.flush()
    refreshed_plan = get_meal_plan(db, plan_id)
    if not refreshed_plan:
        raise ValueError("Meal plan not found after regeneration")

    _recalculate_plan_totals(refreshed_plan)
    _refresh_plan_state(db, refreshed_plan, profile)
    db.commit()
    return get_meal_plan(db, plan_id)


def _weekly_calorie_target(profile: PreferenceProfile) -> Optional[int]:
    if not profile.calorie_target:
        return None
    return profile.calorie_target * 7 * profile.people_count


def _run_validation_checks(plan: models.MealPlan, profile: PreferenceProfile) -> List[dict]:
    issues: List[dict] = []
    weekly_target = _weekly_calorie_target(profile)
    if weekly_target:
        delta = abs(plan.total_calories - weekly_target)
        tolerance = weekly_target * CALORIE_TOLERANCE
        if delta > tolerance:
            issues.append(
                {
                    "code": "calorie_target_miss",
                    "severity": "error",
                    "message": (
                        "Weekly calories differ from target by "
                        f"{round((delta / weekly_target) * 100, 1)}% (target {weekly_target}, actual {plan.total_calories})."
                    ),
                }
            )

    if profile.budget_per_week and plan.total_estimated_cost > profile.budget_per_week:
        issues.append(
            {
                "code": "budget_exceeded",
                "severity": "error",
                "message": (
                    f"Plan cost ${plan.total_estimated_cost:.2f} exceeds weekly budget of ${profile.budget_per_week:.2f}."
                ),
            }
        )

    for item in plan.items:
        record = _recipe_id_lookup().get(str(item.recipe_id))
        if not record:
            issues.append(
                {
                    "code": "recipe_metadata_missing",
                    "severity": "warning",
                    "message": f"Recipe metadata missing for '{item.recipe_title}' ({item.recipe_id}).",
                }
            )
            continue

        if _violates_diet(record, profile.dietary_restrictions):
            issues.append(
                {
                    "code": "dietary_restriction_violation",
                    "severity": "error",
                    "message": f"Meal '{record.title}' conflicts with dietary restrictions {profile.dietary_restrictions}.",
                }
            )

        if _violates_allergies(record, profile.allergies):
            issues.append(
                {
                    "code": "allergy_violation",
                    "severity": "error",
                    "message": f"Meal '{record.title}' includes an allergen from {profile.allergies}.",
                }
            )

        slot = _slot_for_item(profile, item)
        if slot.max_prep_time and item.prep_time_minutes and item.prep_time_minutes > slot.max_prep_time:
            issues.append(
                {
                    "code": "prep_time_exceeded",
                    "severity": "warning",
                    "message": (
                        f"Meal '{record.title}' requires {item.prep_time_minutes} minutes "
                        f"(limit {slot.max_prep_time} minutes)."
                    ),
                }
            )

    return issues


def validate_meal_plan(
    db: Session,
    user_id: str,
    plan_id: str,
    preferences_override: Optional[MealPlanPreferencesOverride] = None,
    refresh: bool = False,
) -> dict:
    if preferences_override is not None:
        refresh = True

    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise ValueError("Meal plan not found")
    if str(plan.user_id) != str(user_id):
        raise ValueError("Not authorized to validate this meal plan")

    if not refresh and plan.last_validated_at and plan.validation_issues is not None:
        return {
            "plan_id": plan.id,
            "is_valid": bool(plan.is_valid),
            "issues": plan.validation_issues or [],
        }

    user = _load_user_with_preferences(db, user_id)
    if not user:
        raise ValueError("User not found")

    profile = _build_preference_profile(user.preferences, preferences_override)
    _refresh_plan_state(db, plan, profile, refresh_summary=False)
    db.commit()
    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise ValueError("Meal plan not found")

    return {
        "plan_id": plan.id,
        "is_valid": bool(plan.is_valid),
        "issues": plan.validation_issues or [],
    }


def summarize_meal_plan(
    db: Session,
    user_id: str,
    plan_id: str,
    refresh: bool = False,
) -> dict:
    plan = get_meal_plan(db, plan_id)
    if not plan:
        raise ValueError("Meal plan not found")
    if str(plan.user_id) != str(user_id):
        raise ValueError("Not authorized to view this meal plan")

    dirty = False
    if refresh or not plan.summary_snapshot:
        _ensure_summary_snapshot(plan, refresh=True)
        dirty = True

    if dirty:
        db.add(plan)
        db.commit()
        plan = get_meal_plan(db, plan_id)
        if not plan:
            raise ValueError("Meal plan not found")

    snapshot = plan.summary_snapshot or {}
    return _hydrate_summary_response(plan, snapshot)

