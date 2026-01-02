// Migration: Add Nutrition Properties to Neo4j
// Created: 2026-01-02
// Description: Adds nutrition and dietary properties to Recipe and Ingredient nodes

// ========================================
// 1. Add Nutrition Properties to Recipe Nodes
// ========================================
MATCH (r:Recipe)
SET r.calories_per_serving = null,
    r.protein_g = null,
    r.carbs_g = null,
    r.fat_g = null,
    r.fiber_g = null,
    r.sugar_g = null,
    r.sodium_mg = null,
    r.saturated_fat_g = null,
    r.health_score = null;

// ========================================
// 2. Add Dietary Classification to Recipes
// ========================================
MATCH (r:Recipe)
SET r.is_vegetarian = false,
    r.is_vegan = false,
    r.is_gluten_free = false,
    r.is_dairy_free = false,
    r.is_keto_friendly = false,
    r.is_low_carb = false,
    r.is_high_protein = false,
    r.is_paleo = false,
    r.allergens = [];

// ========================================
// 3. Add Nutrition Properties to Ingredient Nodes
// ========================================
MATCH (i:Ingredient)
SET i.calories_per_100g = null,
    i.protein_g_per_100g = null,
    i.carbs_g_per_100g = null,
    i.fat_g_per_100g = null,
    i.common_allergen = false,
    i.allergen_type = null; // 'nuts', 'dairy', 'gluten', 'shellfish', 'eggs', 'soy', 'fish'

// ========================================
// 4. Create Indexes for Dietary Filtering
// ========================================
CREATE INDEX recipe_vegetarian IF NOT EXISTS FOR (r:Recipe) ON (r.is_vegetarian);
CREATE INDEX recipe_vegan IF NOT EXISTS FOR (r:Recipe) ON (r.is_vegan);
CREATE INDEX recipe_gluten_free IF NOT EXISTS FOR (r:Recipe) ON (r.is_gluten_free);
CREATE INDEX recipe_keto IF NOT EXISTS FOR (r:Recipe) ON (r.is_keto_friendly);
CREATE INDEX recipe_health_score IF NOT EXISTS FOR (r:Recipe) ON (r.health_score);

// ========================================
// 5. Mark Common Allergen Ingredients
// ========================================

// Nuts
MATCH (i:Ingredient)
WHERE toLower(i.name) CONTAINS 'peanut' 
   OR toLower(i.name) CONTAINS 'almond'
   OR toLower(i.name) CONTAINS 'walnut'
   OR toLower(i.name) CONTAINS 'cashew'
   OR toLower(i.name) CONTAINS 'pecan'
   OR toLower(i.name) CONTAINS 'hazelnut'
SET i.common_allergen = true, i.allergen_type = 'nuts';

// Dairy
MATCH (i:Ingredient)
WHERE toLower(i.name) CONTAINS 'milk'
   OR toLower(i.name) CONTAINS 'cheese'
   OR toLower(i.name) CONTAINS 'butter'
   OR toLower(i.name) CONTAINS 'cream'
   OR toLower(i.name) CONTAINS 'yogurt'
SET i.common_allergen = true, i.allergen_type = 'dairy';

// Gluten
MATCH (i:Ingredient)
WHERE toLower(i.name) CONTAINS 'wheat'
   OR toLower(i.name) CONTAINS 'flour'
   OR toLower(i.name) CONTAINS 'bread'
   OR toLower(i.name) CONTAINS 'pasta'
   OR toLower(i.name) CONTAINS 'barley'
   OR toLower(i.name) CONTAINS 'rye'
SET i.common_allergen = true, i.allergen_type = 'gluten';

// Shellfish
MATCH (i:Ingredient)
WHERE toLower(i.name) CONTAINS 'shrimp'
   OR toLower(i.name) CONTAINS 'crab'
   OR toLower(i.name) CONTAINS 'lobster'
   OR toLower(i.name) CONTAINS 'clam'
   OR toLower(i.name) CONTAINS 'oyster'
   OR toLower(i.name) CONTAINS 'mussel'
SET i.common_allergen = true, i.allergen_type = 'shellfish';

// Eggs
MATCH (i:Ingredient)
WHERE toLower(i.name) CONTAINS 'egg'
SET i.common_allergen = true, i.allergen_type = 'eggs';

// Soy
MATCH (i:Ingredient)
WHERE toLower(i.name) CONTAINS 'soy'
   OR toLower(i.name) CONTAINS 'tofu'
   OR toLower(i.name) CONTAINS 'tempeh'
   OR toLower(i.name) CONTAINS 'edamame'
SET i.common_allergen = true, i.allergen_type = 'soy';

// Fish
MATCH (i:Ingredient)
WHERE toLower(i.name) CONTAINS 'salmon'
   OR toLower(i.name) CONTAINS 'tuna'
   OR toLower(i.name) CONTAINS 'cod'
   OR toLower(i.name) CONTAINS 'tilapia'
   OR toLower(i.name) CONTAINS 'fish'
SET i.common_allergen = true, i.allergen_type = 'fish';

// ========================================
// 6. Verify Migration
// ========================================
// Count recipes with nutrition properties
MATCH (r:Recipe)
RETURN count(r) as total_recipes,
       count(r.health_score) as recipes_with_health_score,
       count(r.is_vegetarian) as recipes_with_dietary_info;

// Count ingredients with allergen info
MATCH (i:Ingredient)
WHERE i.common_allergen = true
RETURN i.allergen_type as allergen, count(i) as count
ORDER BY count DESC;

