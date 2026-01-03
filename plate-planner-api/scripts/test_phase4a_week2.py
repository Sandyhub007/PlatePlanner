#!/usr/bin/env python3
"""
Test Script for Phase 4A Week 2 - Dietary Intelligence
Tests dietary classification, allergen detection, and healthy alternatives
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.dietary_classifier import DietaryClassifier
from src.services.healthy_alternatives import HealthyAlternativesService
from src.services.neo4j_service import Neo4jService
from src.schemas.nutrition import DietaryRestriction, Allergen

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


def test_vegetarian_classification():
    """Test vegetarian classification"""
    print_section("TEST 1: Vegetarian Classification")
    
    try:
        neo4j = Neo4jService()
        classifier = DietaryClassifier(neo4j)
        
        test_cases = [
            (["tomato", "lettuce", "onion", "olive oil"], True, "Salad"),
            (["chicken breast", "lettuce", "tomato"], False, "Chicken Salad"),
            (["tofu", "vegetables", "rice"], True, "Tofu Stir Fry"),
            (["salmon", "asparagus", "lemon"], False, "Grilled Salmon"),
        ]
        
        print("\n✅ Testing vegetarian classification:")
        passed = 0
        for ingredients, expected, dish_name in test_cases:
            result = classifier._is_vegetarian(ingredients)
            status = "✓" if result == expected else "✗"
            print(f"   {status} {dish_name}: {result} (expected {expected})")
            if result == expected:
                passed += 1
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Accuracy: {success_rate:.1f}% ({passed}/{len(test_cases)})")
        
        assert passed >= len(test_cases) * 0.75, "Accuracy below 75%"
        print(f"🎯 Vegetarian Classification: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Vegetarian Classification Test Failed: {e}")
        logger.exception("Classification error")
        return False


def test_vegan_classification():
    """Test vegan classification"""
    print_section("TEST 2: Vegan Classification")
    
    try:
        neo4j = Neo4jService()
        classifier = DietaryClassifier(neo4j)
        
        test_cases = [
            (["quinoa", "chickpeas", "avocado"], True, "Quinoa Bowl"),
            (["pasta", "tomato sauce", "cheese"], False, "Pasta with Cheese"),
            (["vegetables", "egg", "rice"], False, "Fried Rice"),
            (["lentils", "vegetables", "olive oil"], True, "Lentil Soup"),
        ]
        
        print("\n✅ Testing vegan classification:")
        passed = 0
        for ingredients, expected, dish_name in test_cases:
            result = classifier._is_vegan(ingredients)
            status = "✓" if result == expected else "✗"
            print(f"   {status} {dish_name}: {result} (expected {expected})")
            if result == expected:
                passed += 1
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Accuracy: {success_rate:.1f}% ({passed}/{len(test_cases)})")
        
        assert passed >= len(test_cases) * 0.75, "Accuracy below 75%"
        print(f"🎯 Vegan Classification: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Vegan Classification Test Failed: {e}")
        logger.exception("Classification error")
        return False


def test_gluten_free_classification():
    """Test gluten-free classification"""
    print_section("TEST 3: Gluten-Free Classification")
    
    try:
        neo4j = Neo4jService()
        classifier = DietaryClassifier(neo4j)
        
        test_cases = [
            (["rice", "chicken", "vegetables"], True, "Chicken Rice Bowl"),
            (["bread", "turkey", "lettuce"], False, "Turkey Sandwich"),
            (["pasta", "tomato", "cheese"], False, "Pasta"),
            (["quinoa", "salmon", "asparagus"], True, "Salmon Quinoa"),
        ]
        
        print("\n✅ Testing gluten-free classification:")
        passed = 0
        for ingredients, expected, dish_name in test_cases:
            result = classifier._is_gluten_free(ingredients)
            status = "✓" if result == expected else "✗"
            print(f"   {status} {dish_name}: {result} (expected {expected})")
            if result == expected:
                passed += 1
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Accuracy: {success_rate:.1f}% ({passed}/{len(test_cases)})")
        
        assert passed >= len(test_cases) * 0.75, "Accuracy below 75%"
        print(f"🎯 Gluten-Free Classification: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Gluten-Free Classification Test Failed: {e}")
        logger.exception("Classification error")
        return False


def test_allergen_detection():
    """Test allergen detection"""
    print_section("TEST 4: Allergen Detection")
    
    try:
        neo4j = Neo4jService()
        classifier = DietaryClassifier(neo4j)
        
        test_cases = [
            (["peanut butter", "bread", "jelly"], ["peanuts", "nuts"], "PB&J"),
            (["milk", "flour", "sugar"], ["dairy"], "Cake"),
            (["shrimp", "garlic", "butter"], ["shellfish", "dairy"], "Shrimp Scampi"),
            (["chicken", "rice", "broccoli"], [], "Chicken Rice"),
        ]
        
        print("\n✅ Testing allergen detection:")
        passed = 0
        for ingredients, expected_allergens, dish_name in test_cases:
            detected = classifier._detect_allergens(ingredients)
            
            # Check if at least one expected allergen was detected
            if not expected_allergens:
                success = len(detected) == 0
            else:
                success = any(exp in detected for exp in expected_allergens)
            
            status = "✓" if success else "✗"
            print(f"   {status} {dish_name}:")
            print(f"      Detected: {detected}")
            print(f"      Expected: {expected_allergens}")
            
            if success:
                passed += 1
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Accuracy: {success_rate:.1f}% ({passed}/{len(test_cases)})")
        
        assert passed >= len(test_cases) * 0.75, "Accuracy below 75%"
        print(f"🎯 Allergen Detection: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Allergen Detection Test Failed: {e}")
        logger.exception("Allergen detection error")
        return False


def test_dietary_filtering():
    """Test dietary filtering query generation"""
    print_section("TEST 5: Dietary Filtering")
    
    try:
        neo4j = Neo4jService()
        classifier = DietaryClassifier(neo4j)
        
        print("\n✅ Testing dietary filter generation:")
        
        # Test 1: Single restriction
        filter1 = classifier.filter_recipes_by_dietary_needs(
            [DietaryRestriction.VEGETARIAN],
            []
        )
        print(f"\n   Test 1: Vegetarian only")
        print(f"   Filter: {filter1}")
        assert "is_vegetarian = true" in filter1
        print(f"   ✓ PASS")
        
        # Test 2: Multiple restrictions
        filter2 = classifier.filter_recipes_by_dietary_needs(
            [DietaryRestriction.VEGAN, DietaryRestriction.GLUTEN_FREE],
            []
        )
        print(f"\n   Test 2: Vegan + Gluten-free")
        print(f"   Filter: {filter2}")
        assert "is_vegan = true" in filter2
        assert "is_gluten_free = true" in filter2
        print(f"   ✓ PASS")
        
        # Test 3: With allergens
        filter3 = classifier.filter_recipes_by_dietary_needs(
            [DietaryRestriction.VEGETARIAN],
            [Allergen.DAIRY, Allergen.NUTS]
        )
        print(f"\n   Test 3: Vegetarian without dairy/nuts")
        print(f"   Filter: {filter3}")
        assert "NOT 'dairy' IN r.allergens" in filter3
        assert "NOT 'nuts' IN r.allergens" in filter3
        print(f"   ✓ PASS")
        
        print(f"\n🎯 Dietary Filtering: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Dietary Filtering Test Failed: {e}")
        logger.exception("Filtering error")
        return False


def test_schemas():
    """Test nutrition schemas"""
    print_section("TEST 6: Pydantic Schemas")
    
    try:
        from src.schemas.nutrition import (
            DietaryRestriction, Allergen, GoalType,
            DietaryProfile, RecipeDietaryInfo, NutritionMacros
        )
        
        print("\n✅ Testing schemas:")
        
        # Test DietaryProfile
        profile = DietaryProfile(
            user_id="test-user",
            dietary_restrictions=[DietaryRestriction.VEGETARIAN],
            allergens=[Allergen.NUTS],
            calorie_target=2000
        )
        print(f"   ✓ DietaryProfile: {profile.dietary_restrictions}")
        
        # Test RecipeDietaryInfo
        dietary_info = RecipeDietaryInfo(
            is_vegetarian=True,
            is_vegan=False,
            allergens=[Allergen.DAIRY]
        )
        print(f"   ✓ RecipeDietaryInfo: vegetarian={dietary_info.is_vegetarian}")
        
        # Test NutritionMacros
        macros = NutritionMacros(
            calories=350,
            protein_g=30,
            carbs_g=40,
            fat_g=15
        )
        print(f"   ✓ NutritionMacros: {macros.calories} calories")
        
        print(f"\n🎯 Pydantic Schemas: WORKING ✓")
        return True
        
    except Exception as e:
        print(f"\n❌ Pydantic Schemas Test Failed: {e}")
        logger.exception("Schema error")
        return False


def main():
    """Run all Week 2 tests"""
    print("\n" + "█"*70)
    print("  PHASE 4A - WEEK 2 TESTING")
    print("  Intelligence: Dietary Classification, Allergen Detection")
    print("█"*70)
    
    results = {}
    
    # Test 1: Vegetarian Classification
    results['vegetarian'] = test_vegetarian_classification()
    
    # Test 2: Vegan Classification
    results['vegan'] = test_vegan_classification()
    
    # Test 3: Gluten-Free Classification
    results['gluten_free'] = test_gluten_free_classification()
    
    # Test 4: Allergen Detection
    results['allergen_detection'] = test_allergen_detection()
    
    # Test 5: Dietary Filtering
    results['dietary_filtering'] = test_dietary_filtering()
    
    # Test 6: Schemas
    results['schemas'] = test_schemas()
    
    # Summary
    print_section("WEEK 2 TEST SUMMARY")
    
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
        print("\n✅ Week 2 Dietary Intelligence is WORKING CORRECTLY!")
        return 0
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total} passed)")
        print(f"{'='*70}")
        print("\n❌ Please review the failed tests above")
        return 1


if __name__ == "__main__":
    sys.exit(main())

