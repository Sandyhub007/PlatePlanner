from __future__ import annotations

from sqlalchemy import text

from src.database.session import engine


MEAL_PLAN_ALTERS = [
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_calories INTEGER DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_protein INTEGER DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_carbs INTEGER DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_fat INTEGER DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS total_estimated_cost DOUBLE PRECISION DEFAULT 0",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS validation_issues JSONB DEFAULT '[]'::jsonb",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS last_validated_at TIMESTAMP",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS summary_snapshot JSONB DEFAULT '{}'::jsonb",
    "ALTER TABLE meal_plans ADD COLUMN IF NOT EXISTS summary_generated_at TIMESTAMP",
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


# ===== Phase 3: Shopping Lists Schema =====

def ensure_phase_three_schema() -> None:
    """Idempotent helper to create Phase 3 shopping list tables."""
    with engine.begin() as connection:
        # Create shopping_lists table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                plan_id UUID REFERENCES meal_plans(id) ON DELETE SET NULL,
                
                name VARCHAR(255) DEFAULT 'Shopping List',
                status VARCHAR(50) DEFAULT 'active',
                
                total_estimated_cost DOUBLE PRECISION DEFAULT 0.0,
                total_items INTEGER DEFAULT 0,
                purchased_items INTEGER DEFAULT 0,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """))
        
        # Create indexes for shopping_lists
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shopping_lists_user_id 
            ON shopping_lists(user_id)
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shopping_lists_plan_id 
            ON shopping_lists(plan_id)
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shopping_lists_status 
            ON shopping_lists(status)
        """))
        
        # Create shopping_list_items table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS shopping_list_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                list_id UUID NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE,
                
                ingredient_name VARCHAR(255) NOT NULL,
                normalized_name VARCHAR(255),
                
                quantity DOUBLE PRECISION,
                unit VARCHAR(50),
                
                category VARCHAR(100) DEFAULT 'Other',
                
                estimated_price DOUBLE PRECISION,
                store_prices JSONB,
                
                is_purchased BOOLEAN DEFAULT FALSE,
                is_manual BOOLEAN DEFAULT FALSE,
                
                recipe_references TEXT[],
                
                notes TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create indexes for shopping_list_items
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shopping_list_items_list_id 
            ON shopping_list_items(list_id)
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shopping_list_items_category 
            ON shopping_list_items(category)
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shopping_list_items_is_purchased 
            ON shopping_list_items(is_purchased)
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_shopping_list_items_normalized_name 
            ON shopping_list_items(normalized_name)
        """))
