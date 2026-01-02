# 🥗 Phase 4A: Nutritional Analysis & Health Dashboard - Requirements

**Project:** Plate Planner API  
**Phase:** 4A - Nutritional Intelligence  
**Timeline:** 4 weeks (January 2 - January 30, 2026)  
**Status:** 🚀 In Progress  
**Owner:** Sandilya Chimalamarri

---

## 🎯 Executive Summary

Phase 4A transforms Plate Planner from a meal planning tool into a **comprehensive health platform** by adding:
- Real-time nutrition tracking
- Dietary restriction enforcement
- Health-aware recipe recommendations
- Personalized goal tracking

**Value Proposition:** Help users achieve their health goals while enjoying delicious meals.

---

## 📋 Objectives

### Primary Goals
1. **Nutrition Intelligence**: Calculate accurate nutrition for all recipes
2. **Dietary Compliance**: Filter recipes by dietary restrictions & allergens
3. **Health Tracking**: Enable users to set and monitor nutrition goals
4. **Smart Recommendations**: Rank recipes by health score + taste

### Success Metrics
- ✅ 80%+ recipes have USDA-validated nutrition data
- ✅ Dietary filtering accuracy >95%
- ✅ Nutrition calculation accuracy ±10%
- ✅ Health score correlation with dietary guidelines >0.8
- ✅ API response time <300ms (p95)

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Client Application                       │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI - New Routes                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │         /nutrition Router                          │  │
│  │  GET  /nutrition/recipe/{id}                       │  │
│  │  GET  /nutrition/meal-plan/{id}                    │  │
│  │  GET  /nutrition/summary                           │  │
│  │  POST /nutrition/goals                             │  │
│  │  GET  /nutrition/goals/progress                    │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────┐
│            Nutrition Service Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ USDA API Client │  │ Nutrition       │               │
│  │ - Fetch data    │  │ Calculator      │               │
│  │ - Cache results │  │ - Aggregate     │               │
│  │ - Handle errors │  │ - Estimate      │               │
│  └─────────────────┘  └─────────────────┘               │
│                                                           │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │ Health Scorer   │  │ Dietary Filter  │               │
│  │ - Score recipes │  │ - Check restrictions            │
│  │ - Rank by health│  │ - Detect allergens              │
│  └─────────────────┘  └─────────────────┘               │
└────────────────────┬─────────────────────────────────────┘
                     │
       ┌─────────────┼─────────────┐
       │             │             │
       ▼             ▼             ▼
┌────────────┐ ┌──────────┐ ┌──────────────┐
│ PostgreSQL │ │  Neo4j   │ │  USDA API    │
│            │ │          │ │  (External)  │
│ - Nutrition│ │ - Recipe │ │ - FoodData   │
│   goals    │ │   + nutrition │  Central   │
│ - Logs     │ │   props  │ │              │
│ - Cache    │ │          │ │              │
└────────────┘ └──────────┘ └──────────────┘
```

---

## 💾 Database Schema

### PostgreSQL Tables

```sql
-- Ingredient Nutrition Cache (USDA data)
CREATE TABLE ingredient_nutrition (
    id SERIAL PRIMARY KEY,
    ingredient_name VARCHAR(255) UNIQUE NOT NULL,
    normalized_name VARCHAR(255) NOT NULL,
    usda_fdc_id INT, -- FoodData Central ID
    
    -- Macronutrients (per 100g)
    calories INT NOT NULL,
    protein_g DECIMAL(6, 2) NOT NULL,
    carbs_g DECIMAL(6, 2) NOT NULL,
    fat_g DECIMAL(6, 2) NOT NULL,
    fiber_g DECIMAL(6, 2),
    sugar_g DECIMAL(6, 2),
    sodium_mg INT,
    
    -- Micronutrients (optional)
    vitamin_a_mcg INT,
    vitamin_c_mg INT,
    calcium_mg INT,
    iron_mg DECIMAL(5, 2),
    potassium_mg INT,
    
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'usda', -- 'usda', 'manual', 'estimated'
    confidence_score DECIMAL(3, 2) DEFAULT 1.0, -- 0.0 to 1.0
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_ingredient_name (ingredient_name),
    INDEX idx_normalized_name (normalized_name),
    INDEX idx_usda_fdc_id (usda_fdc_id)
);

-- User Nutrition Preferences & Goals
ALTER TABLE users 
    ADD COLUMN dietary_restrictions TEXT[] DEFAULT '{}',
    ADD COLUMN allergens TEXT[] DEFAULT '{}',
    ADD COLUMN daily_calorie_target INT,
    ADD COLUMN daily_protein_g_target INT,
    ADD COLUMN daily_carbs_g_target INT,
    ADD COLUMN daily_fat_g_target INT,
    ADD COLUMN health_goal VARCHAR(50); -- 'weight_loss', 'muscle_gain', 'maintenance', 'general_health'

-- Nutrition Goals Tracking
CREATE TABLE nutrition_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    goal_type VARCHAR(50) NOT NULL, -- 'weight_loss', 'muscle_gain', 'maintenance'
    
    daily_calorie_target INT NOT NULL,
    daily_protein_g_target INT,
    daily_carbs_g_target INT,
    daily_fat_g_target INT,
    
    start_date DATE NOT NULL,
    end_date DATE,
    
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_is_active (is_active)
);

-- Daily Nutrition Logs (aggregated from meal plans)
CREATE TABLE nutrition_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    
    total_calories INT DEFAULT 0,
    total_protein_g INT DEFAULT 0,
    total_carbs_g INT DEFAULT 0,
    total_fat_g INT DEFAULT 0,
    total_fiber_g INT DEFAULT 0,
    
    meals_count INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, log_date),
    INDEX idx_user_id_date (user_id, log_date)
);
```

### Neo4j Schema Updates

```cypher
// Add nutrition properties to Recipe nodes
MATCH (r:Recipe)
SET r.calories_per_serving = null,
    r.protein_g = null,
    r.carbs_g = null,
    r.fat_g = null,
    r.fiber_g = null,
    r.sugar_g = null,
    r.sodium_mg = null,
    r.health_score = null;

// Add dietary classification properties
MATCH (r:Recipe)
SET r.is_vegetarian = false,
    r.is_vegan = false,
    r.is_gluten_free = false,
    r.is_dairy_free = false,
    r.is_keto_friendly = false,
    r.is_low_carb = false,
    r.is_high_protein = false,
    r.allergens = [];

// Add nutrition properties to Ingredient nodes
MATCH (i:Ingredient)
SET i.calories_per_100g = null,
    i.protein_g_per_100g = null,
    i.common_allergen = false;
```

---

## 🔌 API Endpoints

### 1. Get Recipe Nutrition

```http
GET /nutrition/recipe/{recipe_id}
Authorization: Bearer {token}

Response 200:
{
  "recipe_id": "uuid",
  "recipe_title": "Grilled Chicken Salad",
  "servings": 4,
  "per_serving": {
    "calories": 350,
    "protein_g": 35,
    "carbs_g": 20,
    "fat_g": 15,
    "fiber_g": 5,
    "sugar_g": 8,
    "sodium_mg": 450
  },
  "total_recipe": {
    "calories": 1400,
    "protein_g": 140,
    "carbs_g": 80,
    "fat_g": 60
  },
  "macros_percentage": {
    "protein_pct": 40,
    "carbs_pct": 23,
    "fat_pct": 39
  },
  "health_score": 8.5,
  "health_factors": {
    "high_protein": true,
    "low_sodium": false,
    "high_fiber": true
  },
  "dietary_info": {
    "is_vegetarian": false,
    "is_vegan": false,
    "is_gluten_free": true,
    "is_dairy_free": true,
    "is_keto_friendly": true,
    "allergens": []
  },
  "ingredients_nutrition": [
    {
      "ingredient": "chicken breast",
      "quantity": "1 lb",
      "calories": 748,
      "protein_g": 140,
      "data_quality": "usda"
    }
  ]
}
```

### 2. Get Meal Plan Nutrition

```http
GET /nutrition/meal-plan/{plan_id}
Authorization: Bearer {token}

Response 200:
{
  "plan_id": "uuid",
  "week_start": "2026-01-06",
  "week_end": "2026-01-12",
  "total_nutrition": {
    "calories": 14000,
    "protein_g": 700,
    "carbs_g": 1750,
    "fat_g": 466,
    "fiber_g": 210
  },
  "daily_average": {
    "calories": 2000,
    "protein_g": 100,
    "carbs_g": 250,
    "fat_g": 66.5,
    "fiber_g": 30
  },
  "breakdown_by_day": [
    {
      "date": "2026-01-06",
      "day_of_week": "Monday",
      "meals": [
        {
          "meal_type": "breakfast",
          "recipe_id": "uuid",
          "recipe_title": "Oatmeal with Berries",
          "calories": 350,
          "protein_g": 12,
          "carbs_g": 60,
          "fat_g": 8,
          "health_score": 8.0
        },
        {
          "meal_type": "lunch",
          "recipe_id": "uuid",
          "recipe_title": "Grilled Chicken Salad",
          "calories": 450,
          "protein_g": 45,
          "carbs_g": 30,
          "fat_g": 18,
          "health_score": 8.5
        },
        {
          "meal_type": "dinner",
          "recipe_id": "uuid",
          "recipe_title": "Salmon with Vegetables",
          "calories": 550,
          "protein_g": 48,
          "carbs_g": 35,
          "fat_g": 22,
          "health_score": 9.0
        }
      ],
      "daily_total": {
        "calories": 1350,
        "protein_g": 105,
        "carbs_g": 125,
        "fat_g": 48
      }
    }
  ],
  "goal_comparison": {
    "user_has_goals": true,
    "daily_calorie_target": 2000,
    "daily_calorie_actual": 2000,
    "achievement_pct": 100,
    "status": "on_track"
  },
  "health_insights": [
    "Your meal plan meets your calorie goals!",
    "Excellent protein intake this week (35% of calories)",
    "Consider adding more high-fiber foods for better digestion"
  ]
}
```

### 3. Set Nutrition Goals

```http
POST /nutrition/goals
Authorization: Bearer {token}
Content-Type: application/json

{
  "goal_type": "weight_loss",
  "daily_calorie_target": 1800,
  "daily_protein_g_target": 135,
  "daily_carbs_g_target": 180,
  "daily_fat_g_target": 60,
  "start_date": "2026-01-06",
  "duration_days": 90
}

Response 201:
{
  "id": "uuid",
  "user_id": "uuid",
  "goal_type": "weight_loss",
  "daily_targets": {
    "calories": 1800,
    "protein_g": 135,
    "carbs_g": 180,
    "fat_g": 60
  },
  "macro_percentages": {
    "protein_pct": 30,
    "carbs_pct": 40,
    "fat_pct": 30
  },
  "start_date": "2026-01-06",
  "end_date": "2026-04-06",
  "is_active": true,
  "created_at": "2026-01-02T10:00:00Z"
}
```

### 4. Get Nutrition Summary

```http
GET /nutrition/summary?start_date=2026-01-06&end_date=2026-01-12
Authorization: Bearer {token}

Response 200:
{
  "user_id": "uuid",
  "period": {
    "start_date": "2026-01-06",
    "end_date": "2026-01-12",
    "days": 7
  },
  "totals": {
    "calories": 14500,
    "protein_g": 720,
    "carbs_g": 1800,
    "fat_g": 480,
    "fiber_g": 200
  },
  "daily_averages": {
    "calories": 2071,
    "protein_g": 103,
    "carbs_g": 257,
    "fat_g": 68,
    "fiber_g": 28
  },
  "macro_distribution": {
    "protein_pct": 28,
    "carbs_pct": 45,
    "fat_pct": 27
  },
  "goal_progress": {
    "has_active_goal": true,
    "goal_type": "weight_loss",
    "calorie_target": 2000,
    "calorie_actual_avg": 2071,
    "achievement_pct": 103.5,
    "status": "slightly_over",
    "days_on_track": 5,
    "days_off_track": 2
  },
  "health_metrics": {
    "avg_health_score": 7.8,
    "high_protein_meals": 15,
    "low_sodium_meals": 12,
    "high_fiber_meals": 10
  },
  "insights": [
    "You exceeded your calorie goal by 3.5% this week",
    "Great protein intake! You averaged 103g/day (target: 100g)",
    "Your fiber intake is below recommended levels - add more vegetables",
    "Sodium levels are within healthy range"
  ],
  "recommendations": [
    {
      "type": "increase_fiber",
      "message": "Try these high-fiber recipes",
      "recipe_suggestions": ["Quinoa Bowl", "Lentil Soup"]
    }
  ]
}
```

### 5. Get Goal Progress

```http
GET /nutrition/goals/progress
Authorization: Bearer {token}

Response 200:
{
  "active_goal": {
    "id": "uuid",
    "goal_type": "weight_loss",
    "start_date": "2026-01-06",
    "end_date": "2026-04-06",
    "days_elapsed": 3,
    "days_remaining": 87,
    "progress_pct": 3.3
  },
  "targets": {
    "daily_calories": 1800,
    "daily_protein_g": 135,
    "daily_carbs_g": 180,
    "daily_fat_g": 60
  },
  "recent_performance": {
    "last_7_days": {
      "avg_calories": 1850,
      "avg_protein_g": 130,
      "days_on_track": 5,
      "achievement_rate": 71
    },
    "last_30_days": null
  },
  "overall_status": "on_track",
  "next_milestone": {
    "date": "2026-01-20",
    "description": "2 weeks completed"
  }
}
```

---

## 📊 Health Scoring Algorithm

### Formula

```python
health_score = (
    fiber_score * 0.25 +
    protein_score * 0.25 +
    sodium_score * 0.20 +
    sugar_score * 0.15 +
    fat_quality_score * 0.15
)

# Scale: 0-10 (10 = healthiest)
```

### Component Scoring

**Fiber Score (0-10):**
- < 3g: 3
- 3-5g: 5
- 5-8g: 7
- 8-12g: 9
- > 12g: 10

**Protein Score (0-10):**
- < 10g: 3
- 10-20g: 5
- 20-30g: 7
- 30-40g: 9
- > 40g: 10

**Sodium Score (0-10):**
- > 1500mg: 2
- 1000-1500mg: 4
- 700-1000mg: 6
- 400-700mg: 8
- < 400mg: 10

**Sugar Score (0-10):**
- > 25g: 2
- 15-25g: 4
- 10-15g: 6
- 5-10g: 8
- < 5g: 10

**Fat Quality Score (0-10):**
- Based on saturated fat %
- < 10% of total fat: 10
- 10-20%: 7
- 20-30%: 5
- > 30%: 3

### Health Categories
- **9-10**: Excellent (superfoods, nutrient-dense)
- **7-8.9**: Very Good (balanced, healthy)
- **5-6.9**: Good (acceptable, moderate)
- **3-4.9**: Fair (treat occasionally)
- **0-2.9**: Poor (high-calorie, low-nutrient)

---

## 🧪 Week-by-Week Implementation Plan

### **Week 1: Foundation** (Jan 2-8)
**Goal:** USDA integration + database setup

**Tasks:**
- [x] Create Phase 4A requirements document
- [ ] Register for USDA FoodData Central API key
- [ ] Create `ingredient_nutrition` table migration
- [ ] Update `users` table with dietary fields
- [ ] Create `nutrition_goals` and `nutrition_logs` tables
- [ ] Build USDA API client (`src/utils/usda_client.py`)
- [ ] Create nutrition service (`src/services/nutrition_service.py`)
- [ ] Implement `fetch_ingredient_nutrition()` with caching
- [ ] Populate top 500 ingredients from USDA
- [ ] Add nutrition properties to Neo4j Recipe nodes
- [ ] Write unit tests for USDA client

**Deliverables:**
- ✅ Database schema complete
- ✅ 500+ ingredients have USDA nutrition data
- ✅ Basic nutrition calculation working

---

### **Week 2: Intelligence** (Jan 9-15)
**Goal:** Dietary restrictions + health scoring

**Tasks:**
- [ ] Add dietary fields to User Pydantic schemas
- [ ] Create `DietaryProfile` schema
- [ ] Implement dietary classification for recipes
- [ ] Add dietary tags to Neo4j recipes (vegetarian, vegan, etc.)
- [ ] Implement allergen detection algorithm
- [ ] Create health scoring function
- [ ] Update recipe suggestion to filter by dietary needs
- [ ] Implement "healthy alternatives" finder
- [ ] Write unit tests for dietary filtering
- [ ] Write unit tests for health scoring

**Deliverables:**
- ✅ Users can set dietary restrictions
- ✅ Recipes auto-tagged with dietary info
- ✅ Health score calculated for all recipes
- ✅ Dietary filtering working

---

### **Week 3: API** (Jan 16-22)
**Goal:** Build 5 nutrition endpoints

**Tasks:**
- [ ] Create `/nutrition` router
- [ ] Implement `GET /nutrition/recipe/{id}`
- [ ] Implement `GET /nutrition/meal-plan/{id}`
- [ ] Implement `POST /nutrition/goals`
- [ ] Implement `GET /nutrition/summary`
- [ ] Implement `GET /nutrition/goals/progress`
- [ ] Create `NutritionInfo` Pydantic schemas
- [ ] Create `NutritionGoals` Pydantic schemas
- [ ] Add nutrition aggregation for meal plans
- [ ] Implement goal tracking logic
- [ ] Write integration tests for all endpoints
- [ ] Update API documentation

**Deliverables:**
- ✅ 5 endpoints functional
- ✅ Goal tracking working
- ✅ Meal plan nutrition aggregation working
- ✅ Tests passing

---

### **Week 4: Advanced** (Jan 23-30)
**Goal:** Integrate health score + insights

**Tasks:**
- [ ] Integrate health score into recipe ranking algorithm
- [ ] Update hybrid ranking: `score = α·taste + β·ingredients + γ·health`
- [ ] Implement nutrition insights generator
- [ ] Create "healthier alternatives" suggestions
- [ ] Implement weekly nutrition report
- [ ] Add nutrition to shopping list items (optional)
- [ ] Performance optimization (caching, indexing)
- [ ] Full end-to-end testing
- [ ] Documentation (API docs, user guide)
- [ ] Code review and refactoring
- [ ] Bug fixes and polish

**Deliverables:**
- ✅ Health-aware recipe ranking
- ✅ Nutrition insights working
- ✅ Full test coverage
- ✅ Documentation complete
- ✅ **PHASE 4A COMPLETE** 🎉

---

## 🎯 Acceptance Criteria

Phase 4A is complete when:
- [ ] 80%+ of recipes have nutrition data
- [ ] Nutrition calculation accuracy ±10% (validated against USDA)
- [ ] Dietary filtering precision >95%
- [ ] Health score algorithm validated
- [ ] 5 API endpoints fully functional
- [ ] Goal tracking working end-to-end
- [ ] Test coverage >85%
- [ ] API documentation complete
- [ ] Performance benchmarks met (<300ms p95)
- [ ] All code reviewed and merged

---

## 📚 Resources

### External APIs
- **USDA FoodData Central**: https://fdc.nal.usda.gov/api-guide.html
  - Free, 3600 req/hour
  - 1M+ foods with detailed nutrition

### Python Libraries
```bash
poetry add requests  # Already have
poetry add python-dotenv  # For API keys
poetry add aiohttp  # Async HTTP for USDA API
```

### Dietary Guidelines Reference
- USDA Dietary Guidelines: https://www.dietaryguidelines.gov/
- WHO Nutrition Recommendations

---

## 🔐 Environment Variables

```bash
# .env
USDA_API_KEY=your_api_key_here
USDA_API_BASE_URL=https://api.nal.usda.gov/fdc/v1
NUTRITION_CACHE_TTL=86400  # 24 hours
```

---

**Phase 4A Status:** 🚀 **STARTED**  
**Current Week:** Week 1  
**Last Updated:** January 2, 2026  
**Next Milestone:** USDA integration complete (Jan 8)

