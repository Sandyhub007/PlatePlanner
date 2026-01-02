"""
Tests for Dietary Classifier
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.services.dietary_classifier import DietaryClassifier
from src.schemas.nutrition import DietaryRestriction, Allergen


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j service"""
    return Mock()


@pytest.fixture
def classifier(mock_neo4j):
    """Create classifier with mocked Neo4j"""
    return DietaryClassifier(mock_neo4j)


class TestDietaryClassification:
    """Test dietary classification methods"""
    
    def test_is_vegetarian_with_vegetables_only(self, classifier):
        """Test vegetarian classification with only vegetables"""
        ingredients = ["tomato", "lettuce", "onion", "garlic", "olive oil"]
        assert classifier._is_vegetarian(ingredients) == True
    
    def test_is_vegetarian_with_chicken(self, classifier):
        """Test vegetarian classification with chicken"""
        ingredients = ["chicken breast", "tomato", "lettuce"]
        assert classifier._is_vegetarian(ingredients) == False
    
    def test_is_vegetarian_with_fish(self, classifier):
        """Test vegetarian classification with fish"""
        ingredients = ["salmon", "rice", "vegetables"]
        assert classifier._is_vegetarian(ingredients) == False
    
    def test_is_vegan_with_plant_based(self, classifier):
        """Test vegan classification with plant-based ingredients"""
        ingredients = ["tofu", "vegetables", "rice", "olive oil"]
        assert classifier._is_vegan(ingredients) == True
    
    def test_is_vegan_with_dairy(self, classifier):
        """Test vegan classification with dairy"""
        ingredients = ["tofu", "vegetables", "milk"]
        assert classifier._is_vegan(ingredients) == False
    
    def test_is_vegan_with_eggs(self, classifier):
        """Test vegan classification with eggs"""
        ingredients = ["vegetables", "egg", "rice"]
        assert classifier._is_vegan(ingredients) == False
    
    def test_is_pescatarian_with_fish(self, classifier):
        """Test pescatarian classification with fish"""
        ingredients = ["salmon", "vegetables", "rice"]
        assert classifier._is_pescatarian(ingredients) == True
    
    def test_is_pescatarian_with_chicken(self, classifier):
        """Test pescatarian classification with chicken"""
        ingredients = ["chicken", "vegetables"]
        assert classifier._is_pescatarian(ingredients) == False
    
    def test_is_gluten_free_without_wheat(self, classifier):
        """Test gluten-free classification without wheat"""
        ingredients = ["rice", "chicken", "vegetables"]
        assert classifier._is_gluten_free(ingredients) == True
    
    def test_is_gluten_free_with_bread(self, classifier):
        """Test gluten-free classification with bread"""
        ingredients = ["bread", "turkey", "lettuce"]
        assert classifier._is_gluten_free(ingredients) == False
    
    def test_is_gluten_free_with_pasta(self, classifier):
        """Test gluten-free classification with pasta"""
        ingredients = ["pasta", "tomato sauce", "cheese"]
        assert classifier._is_gluten_free(ingredients) == False
    
    def test_is_dairy_free_without_dairy(self, classifier):
        """Test dairy-free classification without dairy"""
        ingredients = ["chicken", "rice", "vegetables"]
        assert classifier._is_dairy_free(ingredients) == True
    
    def test_is_dairy_free_with_cheese(self, classifier):
        """Test dairy-free classification with cheese"""
        ingredients = ["pasta", "cheese", "tomato"]
        assert classifier._is_dairy_free(ingredients) == False
    
    def test_is_keto_friendly_low_carb(self, classifier):
        """Test keto classification with low carb ingredients"""
        ingredients = ["chicken", "avocado", "spinach", "olive oil"]
        assert classifier._is_keto_friendly(ingredients) == True
    
    def test_is_keto_friendly_with_rice(self, classifier):
        """Test keto classification with rice"""
        ingredients = ["chicken", "rice", "vegetables"]
        assert classifier._is_keto_friendly(ingredients) == False
    
    def test_is_high_protein(self, classifier):
        """Test high protein classification"""
        ingredients = ["chicken breast", "greek yogurt", "lentils"]
        assert classifier._is_high_protein(ingredients) == True
    
    def test_is_not_high_protein(self, classifier):
        """Test not high protein classification"""
        ingredients = ["rice", "vegetables", "olive oil"]
        assert classifier._is_high_protein(ingredients) == False


class TestAllergenDetection:
    """Test allergen detection"""
    
    def test_detect_nuts_allergen(self, classifier):
        """Test detection of nuts allergen"""
        ingredients = ["almond", "rice", "honey"]
        allergens = classifier._detect_allergens(ingredients)
        assert "nuts" in allergens or "tree_nuts" in allergens
    
    def test_detect_dairy_allergen(self, classifier):
        """Test detection of dairy allergen"""
        ingredients = ["milk", "flour", "sugar"]
        allergens = classifier._detect_allergens(ingredients)
        assert "dairy" in allergens
    
    def test_detect_gluten_allergen(self, classifier):
        """Test detection of gluten allergen"""
        ingredients = ["wheat flour", "eggs", "butter"]
        allergens = classifier._detect_allergens(ingredients)
        assert "gluten" in allergens or "wheat" in allergens
    
    def test_detect_shellfish_allergen(self, classifier):
        """Test detection of shellfish allergen"""
        ingredients = ["shrimp", "garlic", "butter"]
        allergens = classifier._detect_allergens(ingredients)
        assert "shellfish" in allergens
    
    def test_detect_multiple_allergens(self, classifier):
        """Test detection of multiple allergens"""
        ingredients = ["peanut butter", "milk", "eggs"]
        allergens = classifier._detect_allergens(ingredients)
        assert len(allergens) >= 2
        assert "peanuts" in allergens or "nuts" in allergens
        assert "dairy" in allergens or "eggs" in allergens
    
    def test_no_allergens(self, classifier):
        """Test no allergens detected"""
        ingredients = ["chicken", "rice", "broccoli"]
        allergens = classifier._detect_allergens(ingredients)
        assert len(allergens) == 0


class TestRecipeClassification:
    """Test full recipe classification"""
    
    def test_classify_vegetarian_recipe(self, classifier, mock_neo4j):
        """Test classifying a vegetarian recipe"""
        mock_neo4j.execute_query.return_value = [{
            "title": "Veggie Stir Fry",
            "ingredients": ["tofu", "broccoli", "carrots", "soy sauce", "rice"]
        }]
        
        result = classifier.classify_recipe("recipe-123")
        
        assert result["is_vegetarian"] == True
        assert result["is_vegan"] == False  # soy sauce might have wheat
        assert "soy" in result["allergens"]
    
    def test_classify_vegan_recipe(self, classifier, mock_neo4j):
        """Test classifying a vegan recipe"""
        mock_neo4j.execute_query.return_value = [{
            "title": "Quinoa Bowl",
            "ingredients": ["quinoa", "chickpeas", "avocado", "lemon", "olive oil"]
        }]
        
        result = classifier.classify_recipe("recipe-456")
        
        assert result["is_vegetarian"] == True
        assert result["is_vegan"] == True
        assert result["is_gluten_free"] == True
    
    def test_classify_recipe_not_found(self, classifier, mock_neo4j):
        """Test classifying non-existent recipe"""
        mock_neo4j.execute_query.return_value = []
        
        result = classifier.classify_recipe("nonexistent")
        
        assert result["is_vegetarian"] == False
        assert result["is_vegan"] == False


class TestDietaryFiltering:
    """Test dietary filtering queries"""
    
    def test_filter_by_vegetarian(self, classifier):
        """Test filter query for vegetarian"""
        where_clause = classifier.filter_recipes_by_dietary_needs(
            [DietaryRestriction.VEGETARIAN],
            []
        )
        assert "r.is_vegetarian = true" in where_clause
        assert "WHERE" in where_clause
    
    def test_filter_by_vegan(self, classifier):
        """Test filter query for vegan"""
        where_clause = classifier.filter_recipes_by_dietary_needs(
            [DietaryRestriction.VEGAN],
            []
        )
        assert "r.is_vegan = true" in where_clause
    
    def test_filter_by_allergen(self, classifier):
        """Test filter query for allergen"""
        where_clause = classifier.filter_recipes_by_dietary_needs(
            [],
            [Allergen.NUTS]
        )
        assert "NOT 'nuts' IN r.allergens" in where_clause
    
    def test_filter_by_multiple_restrictions(self, classifier):
        """Test filter query for multiple restrictions"""
        where_clause = classifier.filter_recipes_by_dietary_needs(
            [DietaryRestriction.VEGETARIAN, DietaryRestriction.GLUTEN_FREE],
            [Allergen.DAIRY]
        )
        assert "r.is_vegetarian = true" in where_clause
        assert "r.is_gluten_free = true" in where_clause
        assert "NOT 'dairy' IN r.allergens" in where_clause
        assert " AND " in where_clause
    
    def test_filter_with_no_restrictions(self, classifier):
        """Test filter query with no restrictions"""
        where_clause = classifier.filter_recipes_by_dietary_needs([], [])
        assert where_clause == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

