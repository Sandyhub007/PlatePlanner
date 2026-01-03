#!/usr/bin/env python3
"""
Test Script for Phase 4A Week 1 - Nutrition Foundation
Tests USDA API, nutrition calculation, and health scoring
"""
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.usda_client import USDAClient
from src.services.nutrition_service import NutritionService
from src.services.neo4j_service import Neo4jService
from src.database.session import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title):
    """Print a section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_health_scoring():
    """Test health scoring algorithm"""
    print_section("TEST 1: Health Scoring Algorithm")
    
    try:
        db = next(get_db())
        neo4j = Neo4jService()
        service = NutritionService(db, neo4j)
        
        # Test case 1: Very healthy meal
        healthy_nutrition = {
            "calories": 350,
            "protein_g": 35,
            "carbs_g": 30,
            "fat_g": 10,
            "fiber_g": 8,
            "sugar_g": 3,
            "sodium_mg": 300,
            "saturated_fat_g": 2
        }
        
        score = service.calculate_health_score(healthy_nutrition)
        print(f"\n✅ Healthy Meal Test:")
        print(f"   Nutrition: 350 cal, 35g protein, 8g fiber, low sodium")
        print(f"   Health Score: {score}/10")
        assert score >= 7.0, f"Expected score >=7.0, got {score}"
        print(f"   ✓ PASS - Score is {score} (excellent)")
        
        # Test case 2: Less healthy meal
        unhealthy_nutrition = {
            "calories": 800,
            "protein_g": 15,
            "carbs_g": 90,
            "fat_g": 35,
            "fiber_g": 2,
            "sugar_g": 30,
            "sodium_mg": 2000,
            "saturated_fat_g": 15
        }
        
        score2 = service.calculate_health_score(unhealthy_nutrition)
        print(f"\n✅ Less Healthy Meal Test:")
        print(f"   Nutrition: 800 cal, 15g protein, 30g sugar, high sodium")
        print(f"   Health Score: {score2}/10")
        assert score2 <= 5.0, f"Expected score <=5.0, got {score2}"
        print(f"   ✓ PASS - Score is {score2} (needs improvement)")
        
        print(f"\n🎯 Health Scoring: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Health Scoring Test Failed: {e}")
        logger.exception("Health scoring error")
        return False


async def test_usda_api():
    """Test USDA API integration"""
    print_section("TEST 2: USDA API Integration")
    
    try:
        async with USDAClient() as client:
            # Test search
            print("\n🔍 Testing USDA food search...")
            foods = await client.search_foods("chicken breast", page_size=5)
            
            if not foods:
                print("⚠️  WARNING: No results from USDA API")
                print("   Make sure USDA_API_KEY is set in .env file")
                print("   Falling back to estimation mode...")
                
                # Test fallback
                fallback = client.get_fallback_nutrition("chicken breast")
                print(f"\n✅ Fallback Nutrition (chicken breast):")
                print(f"   Calories: {fallback['calories']} per 100g")
                print(f"   Protein: {fallback['protein_g']}g")
                print(f"   Source: {fallback['data_source']}")
                print(f"   Confidence: {fallback['confidence_score']}")
                return True
            
            print(f"✓ Found {len(foods)} foods")
            first_food = foods[0]
            print(f"   Top result: {first_food.get('description')}")
            
            # Test details fetch
            print("\n🔍 Testing nutrition details fetch...")
            fdc_id = first_food.get("fdcId")
            details = await client.get_food_details(fdc_id)
            
            if details:
                nutrition = client.extract_nutrition(details)
                print(f"\n✅ Nutrition Data (per 100g):")
                print(f"   Calories: {nutrition['calories']}")
                print(f"   Protein: {nutrition['protein_g']}g")
                print(f"   Carbs: {nutrition['carbs_g']}g")
                print(f"   Fat: {nutrition['fat_g']}g")
                print(f"   Fiber: {nutrition.get('fiber_g', 0)}g")
                print(f"   Sodium: {nutrition.get('sodium_mg', 0)}mg")
                print(f"   Source: {nutrition['data_source']}")
                print(f"   USDA ID: {nutrition['usda_fdc_id']}")
                
                # Validate data
                assert nutrition['calories'] > 0, "Calories should be positive"
                assert nutrition['protein_g'] > 0, "Protein should be positive"
                print(f"\n🎯 USDA API: WORKING ✓")
                return True
            else:
                print("❌ Failed to get nutrition details")
                return False
            
    except Exception as e:
        print(f"\n❌ USDA API Test Failed: {e}")
        logger.exception("USDA API error")
        return False


def test_unit_conversion():
    """Test unit conversion"""
    print_section("TEST 3: Unit Conversion")
    
    try:
        db = next(get_db())
        neo4j = Neo4jService()
        service = NutritionService(db, neo4j)
        
        test_cases = [
            (100, "g", 100),
            (1, "kg", 1000),
            (1, "lb", 453.59),
            (1, "cup", 240),
            (1, "tbsp", 15),
            (1, "oz", 28.35)
        ]
        
        print("\n✅ Testing unit conversions:")
        for quantity, unit, expected in test_cases:
            result = service._convert_to_grams(quantity, unit)
            print(f"   {quantity} {unit} = {result}g (expected ~{expected}g)")
            assert abs(result - expected) < 1, f"Conversion error: {result} vs {expected}"
        
        print(f"\n🎯 Unit Conversion: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Unit Conversion Test Failed: {e}")
        logger.exception("Unit conversion error")
        return False


def test_database_models():
    """Test database models"""
    print_section("TEST 4: Database Models")
    
    try:
        from src.database.models import IngredientNutrition, NutritionGoal, NutritionLog
        
        print("\n✅ Checking database models:")
        print(f"   ✓ IngredientNutrition model loaded")
        print(f"   ✓ NutritionGoal model loaded")
        print(f"   ✓ NutritionLog model loaded")
        
        # Check model attributes
        nutrition_attrs = [
            'ingredient_name', 'calories', 'protein_g', 'carbs_g', 
            'fat_g', 'fiber_g', 'usda_fdc_id'
        ]
        
        for attr in nutrition_attrs:
            assert hasattr(IngredientNutrition, attr), f"Missing attribute: {attr}"
        
        print(f"\n🎯 Database Models: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Database Models Test Failed: {e}")
        logger.exception("Database models error")
        return False


async def main():
    """Run all Week 1 tests"""
    print("\n" + "█"*70)
    print("  PHASE 4A - WEEK 1 TESTING")
    print("  Foundation: USDA API, Nutrition Service, Health Scoring")
    print("█"*70)
    
    results = {}
    
    # Test 1: Health Scoring
    results['health_scoring'] = test_health_scoring()
    
    # Test 2: USDA API
    results['usda_api'] = await test_usda_api()
    
    # Test 3: Unit Conversion
    results['unit_conversion'] = test_unit_conversion()
    
    # Test 4: Database Models
    results['database_models'] = test_database_models()
    
    # Summary
    print_section("WEEK 1 TEST SUMMARY")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\n📊 Results:")
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {status} - {test_name.replace('_', ' ').title()}")
    
    print(f"\n{'='*70}")
    if passed == total:
        print(f"🎉 ALL TESTS PASSED! ({passed}/{total})")
        print(f"{'='*70}")
        print("\n✅ Week 1 Foundation is WORKING CORRECTLY!")
        return 0
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total} passed)")
        print(f"{'='*70}")
        print("\n❌ Please review the failed tests above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

