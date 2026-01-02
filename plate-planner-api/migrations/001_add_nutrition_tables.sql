-- Migration: Add Nutrition Tables for Phase 4A
-- Created: 2026-01-02
-- Description: Adds tables for ingredient nutrition data, user goals, and nutrition logs

-- ========================================
-- 1. Ingredient Nutrition Cache (USDA data)
-- ========================================
CREATE TABLE IF NOT EXISTS ingredient_nutrition (
    id SERIAL PRIMARY KEY,
    ingredient_name VARCHAR(255) UNIQUE NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    usda_fdc_id INT, -- FoodData Central ID
    
    -- Macronutrients (per 100g)
    calories INT NOT NULL,
    protein_g DECIMAL(6, 2) NOT NULL DEFAULT 0,
    carbs_g DECIMAL(6, 2) NOT NULL DEFAULT 0,
    fat_g DECIMAL(6, 2) NOT NULL DEFAULT 0,
    fiber_g DECIMAL(6, 2) DEFAULT 0,
    sugar_g DECIMAL(6, 2) DEFAULT 0,
    sodium_mg INT DEFAULT 0,
    
    -- Micronutrients (optional)
    vitamin_a_mcg INT DEFAULT 0,
    vitamin_c_mg INT DEFAULT 0,
    calcium_mg INT DEFAULT 0,
    iron_mg DECIMAL(5, 2) DEFAULT 0,
    potassium_mg INT DEFAULT 0,
    
    -- Fat breakdown (optional)
    saturated_fat_g DECIMAL(6, 2) DEFAULT 0,
    trans_fat_g DECIMAL(6, 2) DEFAULT 0,
    
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'usda', -- 'usda', 'manual', 'estimated'
    confidence_score DECIMAL(3, 2) DEFAULT 1.0, -- 0.0 to 1.0
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for ingredient_nutrition
CREATE INDEX idx_ingredient_nutrition_name ON ingredient_nutrition(ingredient_name);
CREATE INDEX idx_ingredient_nutrition_normalized ON ingredient_nutrition(normalized_name);
CREATE INDEX idx_ingredient_nutrition_usda_id ON ingredient_nutrition(usda_fdc_id);
CREATE INDEX idx_ingredient_nutrition_source ON ingredient_nutrition(data_source);

-- ========================================
-- 2. Update Users Table with Dietary Preferences
-- ========================================
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS dietary_restrictions TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS allergens TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS daily_calorie_target INT,
    ADD COLUMN IF NOT EXISTS daily_protein_g_target INT,
    ADD COLUMN IF NOT EXISTS daily_carbs_g_target INT,
    ADD COLUMN IF NOT EXISTS daily_fat_g_target INT,
    ADD COLUMN IF NOT EXISTS health_goal VARCHAR(50); -- 'weight_loss', 'muscle_gain', 'maintenance', 'general_health'

-- ========================================
-- 3. Nutrition Goals Tracking
-- ========================================
CREATE TABLE IF NOT EXISTS nutrition_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    goal_type VARCHAR(50) NOT NULL, -- 'weight_loss', 'muscle_gain', 'maintenance', 'general_health'
    
    daily_calorie_target INT NOT NULL,
    daily_protein_g_target INT,
    daily_carbs_g_target INT,
    daily_fat_g_target INT,
    
    start_date DATE NOT NULL,
    end_date DATE,
    
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for nutrition_goals
CREATE INDEX idx_nutrition_goals_user_id ON nutrition_goals(user_id);
CREATE INDEX idx_nutrition_goals_is_active ON nutrition_goals(is_active);
CREATE INDEX idx_nutrition_goals_dates ON nutrition_goals(start_date, end_date);

-- ========================================
-- 4. Daily Nutrition Logs (aggregated from meal plans)
-- ========================================
CREATE TABLE IF NOT EXISTS nutrition_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    
    total_calories INT DEFAULT 0,
    total_protein_g INT DEFAULT 0,
    total_carbs_g INT DEFAULT 0,
    total_fat_g INT DEFAULT 0,
    total_fiber_g INT DEFAULT 0,
    total_sodium_mg INT DEFAULT 0,
    
    meals_count INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_user_date UNIQUE(user_id, log_date)
);

-- Indexes for nutrition_logs
CREATE INDEX idx_nutrition_logs_user_id ON nutrition_logs(user_id);
CREATE INDEX idx_nutrition_logs_date ON nutrition_logs(log_date);
CREATE INDEX idx_nutrition_logs_user_date ON nutrition_logs(user_id, log_date);

-- ========================================
-- 5. Functions & Triggers
-- ========================================

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to ingredient_nutrition
CREATE TRIGGER update_ingredient_nutrition_updated_at BEFORE UPDATE
    ON ingredient_nutrition FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to nutrition_goals
CREATE TRIGGER update_nutrition_goals_updated_at BEFORE UPDATE
    ON nutrition_goals FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to nutrition_logs
CREATE TRIGGER update_nutrition_logs_updated_at BEFORE UPDATE
    ON nutrition_logs FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 6. Comments for documentation
-- ========================================
COMMENT ON TABLE ingredient_nutrition IS 'Caches nutrition data from USDA FoodData Central API';
COMMENT ON TABLE nutrition_goals IS 'Tracks user nutrition goals and targets';
COMMENT ON TABLE nutrition_logs IS 'Daily aggregated nutrition consumption logs';
COMMENT ON COLUMN ingredient_nutrition.confidence_score IS 'Data quality score: 1.0=verified USDA, 0.5=estimated';
COMMENT ON COLUMN users.dietary_restrictions IS 'Array of dietary preferences: vegetarian, vegan, keto, gluten_free, etc.';
COMMENT ON COLUMN users.allergens IS 'Array of allergens to avoid: nuts, dairy, eggs, shellfish, etc.';

