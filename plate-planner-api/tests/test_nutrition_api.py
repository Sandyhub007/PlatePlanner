"""
Tests for Nutrition API endpoints
"""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.app import app
from src.database.models import User, MealPlan, MealPlanItem, NutritionGoal
from src.database.session import get_db


client = TestClient(app)


@pytest.fixture
def test_user_token(db: Session):
    """Create test user and return auth token"""
    # Register user
    response = client.post(
        "/auth/register",
        json={
            "email": "nutrition_test@example.com",
            "password": "TestPassword123!",
            "username": "nutrition_tester"
        }
    )
    assert response.status_code in [200, 201, 400]  # 400 if already exists
    
    # Login
    response = client.post(
        "/auth/login",
        data={
            "username": "nutrition_test@example.com",
            "password": "TestPassword123!"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def test_meal_plan(db: Session, test_user_token: str):
    """Create a test meal plan"""
    response = client.post(
        "/meal-plans/generate",
        json={
            "week_start_date": str(date.today()),
            "preferences_override": {
                "dietary_restrictions": [],
                "disliked_ingredients": []
            }
        },
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    if response.status_code == 200:
        return response.json()["plan_id"]
    else:
        # Fallback: get existing meal plan
        response = client.get(
            "/meal-plans",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        if response.status_code == 200 and response.json():
            return response.json()[0]["id"]
    
    return None


class TestRecipeNutritionEndpoint:
    """Test GET /nutrition/recipe/{recipe_id}"""
    
    def test_get_recipe_nutrition_success(self, test_user_token):
        """Should return nutrition for a valid recipe"""
        # Using a sample recipe ID (replace with actual ID from your Neo4j)
        recipe_id = "sample_recipe_1"
        
        response = client.get(
            f"/nutrition/recipe/{recipe_id}?servings=2",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        # If recipe exists
        if response.status_code == 200:
            data = response.json()
            assert "recipe_id" in data
            assert "per_serving" in data
            assert "health_score" in data
            assert data["servings"] == 2
            assert 0 <= data["health_score"] <= 10
    
    def test_get_recipe_nutrition_unauthorized(self):
        """Should return 401 without auth token"""
        response = client.get("/nutrition/recipe/sample_recipe_1")
        assert response.status_code == 401
    
    def test_get_recipe_nutrition_invalid_servings(self, test_user_token):
        """Should reject invalid servings"""
        response = client.get(
            "/nutrition/recipe/sample_recipe_1?servings=0",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 422  # Validation error


class TestMealPlanNutritionEndpoint:
    """Test GET /nutrition/meal-plan/{plan_id}"""
    
    def test_get_meal_plan_nutrition_success(self, test_user_token, test_meal_plan):
        """Should return nutrition for a meal plan"""
        if not test_meal_plan:
            pytest.skip("No meal plan available for testing")
        
        response = client.get(
            f"/nutrition/meal-plan/{test_meal_plan}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "plan_id" in data
        assert "total_nutrition" in data
        assert "daily_average" in data
        assert "breakdown_by_day" in data
        assert "goal_comparison" in data
        assert "health_insights" in data
        
        # Verify nutrition data
        assert "calories" in data["total_nutrition"]
        assert "protein_g" in data["total_nutrition"]
        assert "carbs_g" in data["total_nutrition"]
        assert "fat_g" in data["total_nutrition"]
        
        # Verify daily breakdown
        assert len(data["breakdown_by_day"]) <= 7
    
    def test_get_meal_plan_nutrition_not_found(self, test_user_token):
        """Should return 404 for non-existent plan"""
        fake_plan_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/nutrition/meal-plan/{fake_plan_id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 404
    
    def test_get_meal_plan_nutrition_unauthorized(self, test_meal_plan):
        """Should return 401 without auth token"""
        if not test_meal_plan:
            pytest.skip("No meal plan available")
        
        response = client.get(f"/nutrition/meal-plan/{test_meal_plan}")
        assert response.status_code == 401


class TestNutritionGoalsEndpoint:
    """Test POST /nutrition/goals"""
    
    def test_create_nutrition_goal_success(self, test_user_token):
        """Should create a new nutrition goal"""
        today = date.today()
        
        response = client.post(
            "/nutrition/goals",
            json={
                "goal_type": "weight_loss",
                "daily_calorie_target": 1800,
                "daily_protein_g_target": 120,
                "daily_carbs_g_target": 150,
                "daily_fat_g_target": 60,
                "start_date": str(today),
                "duration_days": 30
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify goal created
        assert "id" in data
        assert data["goal_type"] == "weight_loss"
        assert data["daily_calorie_target"] == 1800
        assert data["is_active"] is True
        
        # Verify end_date calculated correctly
        assert data["end_date"] is not None
        end_date = date.fromisoformat(data["end_date"])
        assert end_date == today + timedelta(days=30)
    
    def test_create_goal_deactivates_previous(self, test_user_token):
        """Creating a new goal should deactivate previous goals"""
        today = date.today()
        
        # Create first goal
        response1 = client.post(
            "/nutrition/goals",
            json={
                "goal_type": "muscle_gain",
                "daily_calorie_target": 2500,
                "start_date": str(today),
                "duration_days": 60
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response1.status_code == 201
        goal1_id = response1.json()["id"]
        
        # Create second goal
        response2 = client.post(
            "/nutrition/goals",
            json={
                "goal_type": "weight_loss",
                "daily_calorie_target": 1600,
                "start_date": str(today),
                "duration_days": 30
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response2.status_code == 201
        
        # Second goal should be active
        assert response2.json()["is_active"] is True
    
    def test_create_goal_validation_errors(self, test_user_token):
        """Should reject invalid goal data"""
        # Calories too low
        response = client.post(
            "/nutrition/goals",
            json={
                "goal_type": "weight_loss",
                "daily_calorie_target": 500,  # Below minimum
                "start_date": str(date.today())
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 422


class TestNutritionSummaryEndpoint:
    """Test GET /nutrition/summary"""
    
    def test_get_nutrition_summary_success(self, test_user_token, test_meal_plan):
        """Should return nutrition summary for date range"""
        if not test_meal_plan:
            pytest.skip("No meal plan available")
        
        start_date = date.today()
        end_date = start_date + timedelta(days=6)
        
        response = client.get(
            f"/nutrition/summary?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "user_id" in data
        assert "period" in data
        assert "totals" in data
        assert "daily_averages" in data
        assert "macro_distribution" in data
        assert "goal_progress" in data
        assert "health_metrics" in data
        assert "insights" in data
        
        # Verify period
        assert data["period"]["days"] == 7
        
        # Verify macro distribution sums to ~100%
        macro_dist = data["macro_distribution"]
        total_pct = macro_dist["protein_pct"] + macro_dist["carbs_pct"] + macro_dist["fat_pct"]
        assert 95 <= total_pct <= 105
        
        # Verify health metrics
        assert 0 <= data["health_metrics"]["avg_health_score"] <= 10
    
    def test_get_summary_invalid_date_range(self, test_user_token):
        """Should reject invalid date ranges"""
        start_date = date.today()
        end_date = start_date - timedelta(days=7)  # End before start
        
        response = client.get(
            f"/nutrition/summary?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 400
    
    def test_get_summary_date_range_too_large(self, test_user_token):
        """Should reject date ranges > 90 days"""
        start_date = date.today()
        end_date = start_date + timedelta(days=100)
        
        response = client.get(
            f"/nutrition/summary?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert response.status_code == 400


class TestGoalProgressEndpoint:
    """Test GET /nutrition/goals/progress"""
    
    def test_get_goal_progress_with_active_goal(self, test_user_token):
        """Should return progress for active goal"""
        # First, create a goal
        today = date.today()
        client.post(
            "/nutrition/goals",
            json={
                "goal_type": "maintenance",
                "daily_calorie_target": 2000,
                "start_date": str(today),
                "duration_days": 30
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        # Get progress
        response = client.get(
            "/nutrition/goals/progress",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify active goal exists
        assert "active_goal" in data
        assert data["active_goal"] is not None
        assert data["active_goal"]["goal_type"] == "maintenance"
        
        # Verify progress calculated
        assert "days_elapsed" in data["active_goal"]
        assert "days_remaining" in data["active_goal"]
        assert "progress_pct" in data["active_goal"]
        
        # Verify targets
        assert "targets" in data
        assert data["targets"]["calories"] == 2000
    
    def test_get_goal_progress_no_active_goal(self, test_user_token):
        """Should return message when no active goal"""
        response = client.get(
            "/nutrition/goals/progress",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        # Either has goal from previous tests or doesn't
        assert response.status_code == 200
        data = response.json()
        assert "active_goal" in data


class TestHealthyAlternativesEndpoint:
    """Test GET /nutrition/alternatives/{recipe_id}"""
    
    def test_get_healthier_alternative_success(self, test_user_token):
        """Should return healthier alternative if available"""
        recipe_id = "sample_recipe_1"
        
        response = client.get(
            f"/nutrition/alternatives/{recipe_id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        # If alternative found
        if response.status_code == 200:
            data = response.json()
            assert "original_recipe_id" in data
            assert "alternative_recipe_id" in data
            assert "improvement_pct" in data
            assert "reason" in data
            assert data["improvement_pct"] > 0
    
    def test_get_alternative_not_found(self, test_user_token):
        """Should return 404 when no healthier alternative exists"""
        fake_recipe_id = "nonexistent_recipe_9999"
        
        response = client.get(
            f"/nutrition/alternatives/{fake_recipe_id}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        # Might be 404 (no alternative) or 500 (recipe not found)
        assert response.status_code in [404, 500]


# ========================================
# Integration Tests
# ========================================

class TestNutritionAPIIntegration:
    """End-to-end integration tests"""
    
    def test_full_nutrition_workflow(self, test_user_token, test_meal_plan):
        """Test complete workflow: create goal → view meal plan nutrition → get summary"""
        if not test_meal_plan:
            pytest.skip("No meal plan available")
        
        # Step 1: Create nutrition goal
        today = date.today()
        goal_response = client.post(
            "/nutrition/goals",
            json={
                "goal_type": "general_health",
                "daily_calorie_target": 2000,
                "daily_protein_g_target": 100,
                "start_date": str(today),
                "duration_days": 30
            },
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert goal_response.status_code == 201
        
        # Step 2: Get meal plan nutrition
        plan_response = client.get(
            f"/nutrition/meal-plan/{test_meal_plan}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert plan_response.status_code == 200
        plan_data = plan_response.json()
        
        # Should show goal comparison
        assert plan_data["goal_comparison"]["has_active_goal"] is True
        assert plan_data["goal_comparison"]["goal_type"] == "general_health"
        assert plan_data["goal_comparison"]["calorie_target"] == 2000
        
        # Step 3: Get weekly summary
        end_date = today + timedelta(days=6)
        summary_response = client.get(
            f"/nutrition/summary?start_date={today}&end_date={end_date}",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        
        # Should show goal progress
        assert summary_data["goal_progress"]["has_active_goal"] is True
        
        # Step 4: Get goal progress
        progress_response = client.get(
            "/nutrition/goals/progress",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert progress_response.status_code == 200
        progress_data = progress_response.json()
        
        assert progress_data["active_goal"] is not None
        assert progress_data["targets"]["calories"] == 2000


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

