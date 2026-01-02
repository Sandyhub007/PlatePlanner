"""
Tests for Healthy Alternatives Service
"""
import pytest
from unittest.mock import Mock
from src.services.healthy_alternatives import HealthyAlternativesService
from src.schemas.nutrition import DietaryRestriction, Allergen


@pytest.fixture
def mock_neo4j():
    """Mock Neo4j service"""
    return Mock()


@pytest.fixture
def service(mock_neo4j):
    """Create service with mocked Neo4j"""
    return HealthyAlternativesService(mock_neo4j)


class TestHealthyAlternatives:
    """Test healthy alternatives finder"""
    
    def test_find_healthier_alternative(self, service, mock_neo4j):
        """Test finding a healthier alternative"""
        # Mock original recipe
        mock_neo4j.execute_query.side_effect = [
            [{  # Original recipe
                "id": "recipe-1",
                "title": "Fried Chicken",
                "health_score": 4.0,
                "calories": 500,
                "protein_g": 30,
                "sodium_mg": 1200
            }],
            [{  # Healthier alternative
                "id": "recipe-2",
                "title": "Grilled Chicken",
                "health_score": 7.5,
                "calories": 350,
                "protein_g": 35,
                "sodium_mg": 600,
                "common_ingredients": 5
            }]
        ]
        
        result = service.find_healthier_alternative("recipe-1")
        
        assert result is not None
        assert result.original_recipe_id == "recipe-1"
        assert result.alternative_recipe_id == "recipe-2"
        assert result.alternative_health_score > result.original_health_score
        assert result.improvement_pct > 0
    
    def test_find_healthier_alternative_none_found(self, service, mock_neo4j):
        """Test when no healthier alternative exists"""
        mock_neo4j.execute_query.side_effect = [
            [{  # Original recipe (already healthy)
                "id": "recipe-1",
                "title": "Kale Salad",
                "health_score": 9.5,
                "calories": 150
            }],
            []  # No alternatives found
        ]
        
        result = service.find_healthier_alternative("recipe-1")
        
        assert result is None
    
    def test_find_healthier_alternative_with_dietary_restrictions(self, service, mock_neo4j):
        """Test finding alternative with dietary restrictions"""
        mock_neo4j.execute_query.side_effect = [
            [{
                "id": "recipe-1",
                "title": "Beef Burger",
                "health_score": 5.0,
                "calories": 600
            }],
            [{
                "id": "recipe-2",
                "title": "Veggie Burger",
                "health_score": 7.0,
                "calories": 400,
                "common_ingredients": 3
            }]
        ]
        
        result = service.find_healthier_alternative(
            "recipe-1",
            dietary_restrictions=[DietaryRestriction.VEGETARIAN]
        )
        
        assert result is not None
        # Verify the query included dietary filters
        call_args = mock_neo4j.execute_query.call_args_list[1]
        query = call_args[0][0]
        assert "is_vegetarian" in query.lower()
    
    def test_generate_reason_lower_calories(self, service):
        """Test reason generation for lower calories"""
        original = {"calories": 500, "sodium_mg": 800, "protein_g": 20, "health_score": 5.0}
        alternative = {"calories": 350, "sodium_mg": 700, "protein_g": 25, "health_score": 7.5}
        
        reason = service._generate_reason(original, alternative)
        
        assert "150 fewer calories" in reason
        assert "health score improvement" in reason
    
    def test_generate_reason_lower_sodium(self, service):
        """Test reason generation for lower sodium"""
        original = {"calories": 400, "sodium_mg": 1500, "protein_g": 25, "health_score": 5.0}
        alternative = {"calories": 400, "sodium_mg": 600, "protein_g": 25, "health_score": 7.0}
        
        reason = service._generate_reason(original, alternative)
        
        assert "lower sodium" in reason
    
    def test_generate_reason_higher_protein(self, service):
        """Test reason generation for higher protein"""
        original = {"calories": 400, "sodium_mg": 800, "protein_g": 15, "health_score": 5.0}
        alternative = {"calories": 400, "sodium_mg": 800, "protein_g": 30, "health_score": 7.0}
        
        reason = service._generate_reason(original, alternative)
        
        assert "higher protein" in reason


class TestHealthiestRecipes:
    """Test healthiest recipes suggestions"""
    
    def test_suggest_healthiest_recipes(self, service, mock_neo4j):
        """Test getting healthiest recipes"""
        mock_neo4j.execute_query.return_value = [
            {
                "id": "recipe-1",
                "title": "Quinoa Bowl",
                "health_score": 9.2,
                "calories": 350,
                "protein_g": 18
            },
            {
                "id": "recipe-2",
                "title": "Grilled Salmon",
                "health_score": 8.8,
                "calories": 400,
                "protein_g": 35
            }
        ]
        
        results = service.suggest_healthiest_recipes(limit=10)
        
        assert len(results) == 2
        assert results[0]["health_score"] >= results[1]["health_score"]
    
    def test_suggest_healthiest_recipes_by_meal_type(self, service, mock_neo4j):
        """Test getting healthiest recipes for specific meal type"""
        mock_neo4j.execute_query.return_value = [
            {
                "id": "recipe-1",
                "title": "Oatmeal Bowl",
                "health_score": 8.5,
                "calories": 300
            }
        ]
        
        results = service.suggest_healthiest_recipes(meal_type="breakfast", limit=5)
        
        # Verify query included meal type filter
        call_args = mock_neo4j.execute_query.call_args
        query = call_args[0][0]
        assert "breakfast" in query.lower()
    
    def test_suggest_healthiest_recipes_with_dietary_restrictions(self, service, mock_neo4j):
        """Test getting healthiest recipes with dietary filters"""
        mock_neo4j.execute_query.return_value = []
        
        service.suggest_healthiest_recipes(
            dietary_restrictions=[DietaryRestriction.VEGAN],
            allergens=[Allergen.NUTS],
            limit=5
        )
        
        # Verify query included dietary filters
        call_args = mock_neo4j.execute_query.call_args
        query = call_args[0][0]
        assert "is_vegan" in query.lower()
        assert "NOT 'nuts' IN r.allergens" in query


class TestDietaryFilterBuilder:
    """Test dietary filter building"""
    
    def test_build_filter_with_restrictions(self, service):
        """Test building filter with restrictions"""
        filter_clause = service._build_dietary_filter(
            [DietaryRestriction.VEGETARIAN, DietaryRestriction.GLUTEN_FREE],
            []
        )
        
        assert "r2.is_vegetarian = true" in filter_clause
        assert "r2.is_gluten_free = true" in filter_clause
        assert "AND" in filter_clause
    
    def test_build_filter_with_allergens(self, service):
        """Test building filter with allergens"""
        filter_clause = service._build_dietary_filter(
            [],
            [Allergen.DAIRY, Allergen.NUTS]
        )
        
        assert "NOT 'dairy' IN r2.allergens" in filter_clause
        assert "NOT 'nuts' IN r2.allergens" in filter_clause
    
    def test_build_filter_empty(self, service):
        """Test building filter with no restrictions"""
        filter_clause = service._build_dietary_filter([], [])
        
        assert filter_clause == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

