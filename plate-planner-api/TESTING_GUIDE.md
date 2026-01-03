# 🧪 Phase 4A Testing Guide

**Complete testing instructions for Week 1 & 2**

---

## 📋 Prerequisites

### 1. Docker Services Running
```bash
docker-compose ps
```

**Expected output:**
```
plate-planner-api    running
plate-planner-db     running
plate-planner-neo4j  running
```

If not running:
```bash
docker-compose up -d
```

### 2. Database Migrations (Optional but Recommended)

**PostgreSQL:**
```bash
cat plate-planner-api/migrations/001_add_nutrition_tables.sql | \
  docker exec -i plate-planner-db psql -U postgres -d plateplanner
```

**Neo4j:**
```bash
# Copy migration file
docker cp plate-planner-api/migrations/002_update_neo4j_nutrition.cypher plate-planner-neo4j:/tmp/

# Run it
docker exec -it plate-planner-neo4j cypher-shell -u neo4j -p 12345678 -f /tmp/002_update_neo4j_nutrition.cypher
```

### 3. USDA API Key (Optional)
If you want full USDA API testing:
1. Get key: https://fdc.nal.usda.gov/api-key-signup.html
2. Add to `.env`: `USDA_API_KEY=your_key_here`

*Without API key, fallback estimation mode will be used (still works!)*

---

## 🚀 Quick Testing (Recommended)

### Run All Tests
```bash
cd plate-planner-api

# Test Week 1
python scripts/test_phase4a_week1.py

# Test Week 2
python scripts/test_phase4a_week2.py
```

**Expected:**
```
🎉 ALL TESTS PASSED! (4/4)
✅ Week 1 Foundation is WORKING CORRECTLY!

🎉 ALL TESTS PASSED! (6/6)
✅ Week 2 Dietary Intelligence is WORKING CORRECTLY!
```

---

## 🔬 Detailed Testing

### Week 1: Nutrition Foundation

#### Test 1: Health Scoring Algorithm
```bash
python scripts/test_phase4a_week1.py
```

**What it tests:**
- ✅ Health score calculation (0-10 scale)
- ✅ Multi-factor scoring (fiber, protein, sodium, sugar, fat quality)
- ✅ High-health vs low-health differentiation

**Expected output:**
```
TEST 1: Health Scoring Algorithm
✅ Healthy Meal Test:
   Health Score: 8.2/10
   ✓ PASS - Score is 8.2 (excellent)

✅ Less Healthy Meal Test:
   Health Score: 3.5/10
   ✓ PASS - Score is 3.5 (needs improvement)
```

#### Test 2: USDA API Integration
**What it tests:**
- ✅ USDA food search
- ✅ Nutrition details fetch
- ✅ Data extraction & parsing
- ✅ Fallback estimation mode

**Expected output (with API key):**
```
TEST 2: USDA API Integration
✓ Found 5 foods
   Top result: Chicken, broilers or fryers, breast, meat only, raw

✅ Nutrition Data (per 100g):
   Calories: 165
   Protein: 31.0g
   Fat: 3.6g
   Source: usda
   USDA ID: 171477
```

**Expected output (without API key):**
```
⚠️  WARNING: No results from USDA API
   Falling back to estimation mode...

✅ Fallback Nutrition (chicken breast):
   Calories: 165 per 100g
   Protein: 31.0g
   Source: estimated
   Confidence: 0.5
```

#### Test 3: Unit Conversion
**What it tests:**
- ✅ Volume conversions (cups, ml, liters)
- ✅ Weight conversions (lbs, oz, grams)
- ✅ Count units

**Expected output:**
```
TEST 3: Unit Conversion
✅ Testing unit conversions:
   1 kg = 1000.0g (expected ~1000g)
   1 lb = 453.59g (expected ~453.59g)
   1 cup = 240.0g (expected ~240g)
```

---

### Week 2: Dietary Intelligence

#### Test 1-3: Classification Tests
```bash
python scripts/test_phase4a_week2.py
```

**What it tests:**
- ✅ Vegetarian detection (no meat/fish)
- ✅ Vegan detection (no animal products)
- ✅ Gluten-free detection (no wheat/gluten)
- ✅ Keyword matching accuracy

**Expected output:**
```
TEST 1: Vegetarian Classification
✅ Testing vegetarian classification:
   ✓ Salad: True (expected True)
   ✓ Chicken Salad: False (expected False)
   ✓ Tofu Stir Fry: True (expected True)
   ✓ Grilled Salmon: False (expected False)

📊 Accuracy: 100.0% (4/4)
🎯 Vegetarian Classification: WORKING ✓
```

#### Test 4: Allergen Detection
**What it tests:**
- ✅ 11 allergen types
- ✅ Keyword matching
- ✅ Multiple allergens per recipe

**Expected output:**
```
TEST 4: Allergen Detection
✅ Testing allergen detection:
   ✓ PB&J:
      Detected: ['peanuts', 'nuts', 'gluten']
      Expected: ['peanuts', 'nuts']
   ✓ Shrimp Scampi:
      Detected: ['shellfish', 'dairy']
      Expected: ['shellfish', 'dairy']

📊 Accuracy: 100.0% (4/4)
```

#### Test 5: Dietary Filtering
**What it tests:**
- ✅ Cypher query generation
- ✅ Multiple restrictions
- ✅ Allergen exclusion

**Expected output:**
```
TEST 5: Dietary Filtering
✅ Testing dietary filter generation:
   Test 1: Vegetarian only
   Filter: WHERE r.is_vegetarian = true
   ✓ PASS

   Test 2: Vegan + Gluten-free
   Filter: WHERE r.is_vegan = true AND r.is_gluten_free = true
   ✓ PASS
```

---

## 🧪 Unit Tests (PyTest)

### Run All Unit Tests
```bash
cd plate-planner-api

# Week 1 & 2 unit tests
pytest tests/test_dietary_classifier.py -v
pytest tests/test_healthy_alternatives.py -v

# With coverage report
pytest tests/test_dietary_classifier.py --cov=src/services/dietary_classifier --cov-report=term-missing
```

**Expected output:**
```
tests/test_dietary_classifier.py::TestDietaryClassification::test_is_vegetarian_with_vegetables_only PASSED
tests/test_dietary_classifier.py::TestDietaryClassification::test_is_vegan_with_plant_based PASSED
tests/test_dietary_classifier.py::TestAllergenDetection::test_detect_nuts_allergen PASSED
...
================================ 30 passed in 2.5s ================================
```

---

## 📦 Manual Testing

### Test 1: Classify a Single Recipe

```python
from src.services.neo4j_service import Neo4jService
from src.services.dietary_classifier import DietaryClassifier

neo4j = Neo4jService()
classifier = DietaryClassifier(neo4j)

# Get a recipe ID (replace with actual ID from your database)
result = classifier.classify_recipe("some-recipe-id")

print("Dietary Classification:")
print(f"  Vegetarian: {result['is_vegetarian']}")
print(f"  Vegan: {result['is_vegan']}")
print(f"  Gluten-free: {result['is_gluten_free']}")
print(f"  Allergens: {result['allergens']}")
```

### Test 2: Find Healthier Alternative

```python
from src.services.healthy_alternatives import HealthyAlternativesService
from src.schemas.nutrition import DietaryRestriction

service = HealthyAlternativesService(neo4j)

alt = service.find_healthier_alternative(
    recipe_id="some-recipe-id",
    dietary_restrictions=[DietaryRestriction.VEGETARIAN]
)

if alt:
    print(f"Original: {alt.original_recipe_title} (score: {alt.original_health_score})")
    print(f"Alternative: {alt.alternative_recipe_title} (score: {alt.alternative_health_score})")
    print(f"Improvement: +{alt.improvement_pct}%")
    print(f"Reason: {alt.reason}")
```

### Test 3: Calculate Recipe Nutrition

```python
import asyncio
from src.services.nutrition_service import NutritionService
from src.database.session import get_db

db = next(get_db())
service = NutritionService(db, neo4j)

async def test():
    nutrition = await service.calculate_recipe_nutrition(
        recipe_id="some-recipe-id",
        servings=4
    )
    
    print(f"Recipe: {nutrition['recipe_title']}")
    print(f"Per Serving:")
    print(f"  Calories: {nutrition['per_serving']['calories']}")
    print(f"  Protein: {nutrition['per_serving']['protein_g']}g")
    print(f"  Health Score: {nutrition['health_score']}/10")

asyncio.run(test())
```

---

## 🔍 Troubleshooting

### Issue 1: ModuleNotFoundError

**Error:**
```
ModuleNotFoundError: No module named 'src'
```

**Fix:**
```bash
# Make sure you're in the right directory
cd plate-planner-api

# Run with Python path
PYTHONPATH=. python scripts/test_phase4a_week1.py
```

### Issue 2: Database Connection Failed

**Error:**
```
Could not connect to PostgreSQL/Neo4j
```

**Fix:**
```bash
# Check if services are running
docker-compose ps

# Restart if needed
docker-compose restart

# Check logs
docker logs plate-planner-api
docker logs plate-planner-db
docker logs plate-planner-neo4j
```

### Issue 3: USDA API Rate Limit

**Error:**
```
USDA API error: 429 Too Many Requests
```

**Fix:**
- Wait 1 hour (rate limit: 3600 req/hour)
- Tests will automatically fall back to estimation mode

### Issue 4: No Recipes Found

**Error:**
```
Recipe not found: some-recipe-id
```

**Fix:**
```bash
# Check if Neo4j has recipes
docker exec -it plate-planner-neo4j cypher-shell -u neo4j -p 12345678

# Run query
MATCH (r:Recipe) RETURN count(r);

# If 0, you need to load recipe data first
```

---

## ✅ Success Criteria

### Week 1 Tests Should Show:
- ✅ Health scores calculated correctly (7-10 for healthy, 2-5 for unhealthy)
- ✅ USDA API working OR fallback mode active
- ✅ Unit conversions accurate (±1g tolerance)
- ✅ Database models loaded

### Week 2 Tests Should Show:
- ✅ Classification accuracy >75% for all dietary types
- ✅ Allergen detection working
- ✅ Dietary filters generating correct Cypher queries
- ✅ Schemas validating correctly

---

## 📊 Expected Test Duration

| Test Suite | Duration | Description |
|------------|----------|-------------|
| **Week 1 Quick Test** | 5-10 seconds | Core functionality |
| **Week 2 Quick Test** | 3-5 seconds | Classification logic |
| **PyTest Suite** | 10-30 seconds | All unit tests |
| **Manual Testing** | 2-5 minutes | Interactive exploration |

---

## 🎯 Next Steps After Testing

If all tests pass:
1. ✅ **Week 1 & 2 are production-ready!**
2. Run classification script: `python scripts/classify_all_recipes.py`
3. Ready for Week 3 (API endpoints)

If some tests fail:
1. Check the error messages
2. Review the troubleshooting section
3. Check Docker logs for more details
4. Ask for help with specific error messages

---

## 📞 Getting Help

If tests fail and you need assistance:

1. **Capture the full error:**
```bash
python scripts/test_phase4a_week1.py 2>&1 | tee test_output.txt
```

2. **Check Docker logs:**
```bash
docker logs plate-planner-api --tail 50
```

3. **Share the error** with:
   - The test that failed
   - The error message
   - Docker logs (if relevant)

---

**Happy Testing!** 🧪✨

*Remember: It's OK if USDA API tests warn about no API key - fallback mode still works!*

