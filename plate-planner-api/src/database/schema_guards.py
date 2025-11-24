from __future__ import annotations

from sqlalchemy import text

from src.database.session import engine


MEAL_PLAN_ALTERS = [
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_calories INTEGER DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_protein INTEGER DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_carbs INTEGER DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_fat INTEGER DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_estimated_cost DOUBLE PRECISION DEFAULT 0",
    "ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS protein INTEGER",
    "ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS carbs INTEGER",
    "ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS fat INTEGER",
    "ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS estimated_cost DOUBLE PRECISION DEFAULT 0",
    "ALTER TABLE meal_plan_items ADD COLUMN IF NOT EXISTS prep_time_minutes INTEGER",
]


def ensure_phase_two_schema() -> None:
    """Idempotent helper to add Phase 2 meal-planning columns."""
    with engine.begin() as connection:
        for statement in MEAL_PLAN_ALTERS:
            connection.execute(text(statement))
