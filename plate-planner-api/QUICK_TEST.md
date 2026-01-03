# 🚀 Quick Test - Phase 4A Week 1 & 2

**Run this to test everything in under 1 minute!**

---

## ✅ Prerequisites

1. **Docker running:**
```bash
docker-compose ps
# Should show: api, db, neo4j all running
```

2. **Inside the project:**
```bash
cd /Users/sandilyachimalamarri/Plateplanner/plate-planner-api
```

---

## 🧪 Run Tests

### Option 1: Automated Tests (Recommended)

```bash
# Test Week 1 Foundation
python scripts/test_phase4a_week1.py

# Test Week 2 Intelligence  
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

### Option 2: PyTest (Unit Tests)

```bash
# Week 2 unit tests
pytest tests/test_dietary_classifier.py -v
pytest tests/test_healthy_alternatives.py -v
```

**Expected:**
```
================================ 30 passed ================================
================================ 20 passed ================================
```

---

### Option 3: Quick Manual Test

```python
# Start Python in container
docker exec -it plate-planner-api python

# Test health scoring
from src.services.nutrition_service import NutritionService
from src.services.neo4j_service import Neo4jService
from src.database.session import get_db

db = next(get_db())
neo4j = Neo4jService()
service = NutritionService(db, neo4j)

nutrition = {
    "calories": 350,
    "protein_g": 35,
    "carbs_g": 20,
    "fat_g": 15,
    "fiber_g": 8,
    "sugar_g": 3,
    "sodium_mg": 400,
    "saturated_fat_g": 2
}

score = service.calculate_health_score(nutrition)
print(f"Health Score: {score}/10")  # Should be ~8.5

# Test dietary classification
from src.services.dietary_classifier import DietaryClassifier

classifier = DietaryClassifier(neo4j)

# Test vegetarian detection
result = classifier._is_vegetarian(["tomato", "lettuce", "onion"])
print(f"Is vegetarian: {result}")  # Should be True

result2 = classifier._is_vegetarian(["chicken", "tomato"])
print(f"Is vegetarian: {result2}")  # Should be False

# Test allergen detection
allergens = classifier._detect_allergens(["peanut butter", "milk"])
print(f"Allergens detected: {allergens}")  # Should include peanuts, dairy

exit()
```

---

## 📊 What Gets Tested

### Week 1 Tests (4 total):
1. ✅ **Health Scoring** - Multi-factor algorithm (0-10 scale)
2. ✅ **USDA API** - Food search & nutrition fetch (or fallback)
3. ✅ **Unit Conversion** - Volume, weight, count conversions
4. ✅ **Database Models** - SQLAlchemy models loaded

### Week 2 Tests (6 total):
1. ✅ **Vegetarian Classification** - No meat/fish detection
2. ✅ **Vegan Classification** - No animal products detection
3. ✅ **Gluten-Free Classification** - Wheat/gluten detection
4. ✅ **Allergen Detection** - 11 allergen types
5. ✅ **Dietary Filtering** - Cypher query generation
6. ✅ **Pydantic Schemas** - All schemas validate correctly

---

## 🎯 Expected Results

✅ **All tests should PASS**  
✅ **Classification accuracy: 75-100%**  
✅ **Health scores: 0-10 range**  
✅ **Execution time: <20 seconds total**

---

## ⚠️ Common Issues

### Issue: "USDA API key not found"
**Solution:** This is OK! Tests will use fallback estimation mode.

### Issue: "No recipes found"
**Solution:** Neo4j might not have recipes loaded yet. Classification logic still works!

### Issue: "ModuleNotFoundError"
**Solution:** Run from plate-planner-api directory:
```bash
cd /Users/sandilyachimalamarri/Plateplanner/plate-planner-api
python scripts/test_phase4a_week1.py
```

---

## 📚 Full Testing Guide

For detailed testing instructions, see:
```bash
cat TESTING_GUIDE.md
```

---

## 🎉 Success Looks Like

```
████████████████████████████████████████████████████████████████████
  PHASE 4A - WEEK 1 TESTING
  Foundation: USDA API, Nutrition Service, Health Scoring
████████████████████████████████████████████████████████████████████

══════════════════════════════════════════════════════════════════════
  TEST 1: Health Scoring Algorithm
══════════════════════════════════════════════════════════════════════

✅ Healthy Meal Test:
   Nutrition: 350 cal, 35g protein, 8g fiber, low sodium
   Health Score: 8.5/10
   ✓ PASS - Score is 8.5 (excellent)

✅ Less Healthy Meal Test:
   Nutrition: 800 cal, 15g protein, 30g sugar, high sodium
   Health Score: 3.2/10
   ✓ PASS - Score is 3.2 (needs improvement)

🎯 Health Scoring: WORKING ✓

══════════════════════════════════════════════════════════════════════
  WEEK 1 TEST SUMMARY
══════════════════════════════════════════════════════════════════════

📊 Results:
   ✅ PASS - Health Scoring
   ✅ PASS - Usda Api
   ✅ PASS - Unit Conversion
   ✅ PASS - Database Models

══════════════════════════════════════════════════════════════════════
🎉 ALL TESTS PASSED! (4/4)
══════════════════════════════════════════════════════════════════════

✅ Week 1 Foundation is WORKING CORRECTLY!
```

---

**That's it! Run the tests and see your Phase 4A in action!** 🚀

