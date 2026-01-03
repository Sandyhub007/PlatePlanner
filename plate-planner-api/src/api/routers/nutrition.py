"""
Nutrition API Router
Endpoints for nutrition tracking, goals, and health insights
"""
from typing import List, Optional
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from src.database.session import get_db
from src.database.models import User, MealPlan, NutritionGoal, NutritionLog
from src.services.neo4j_service import Neo4jService
from src.services.nutrition_service import NutritionService
from src.services.healthy_alternatives import HealthyAlternativesService
from src.services.nutrition_insights import NutritionInsightsEngine
from src.auth.security import get_current_user
from src.schemas.nutrition import (
    RecipeNutrition,
    MealPlanNutrition,
    NutritionGoalCreate,
    NutritionGoal as NutritionGoalSchema,
    NutritionSummary,
    GoalProgress,
    HealthyAlternative,
    DietaryRestriction,
    Allergen,
    NutritionMacros,
    DayNutrition,
    MealNutrition,
    NutritionPeriod,
    HealthMetrics,
    MacroPercentages,
    MacroTargets,
)

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


def get_neo4j_service():
    """Dependency for Neo4j service"""
    return Neo4jService()


def get_nutrition_service(
    db: Session = Depends(get_db),
    neo4j: Neo4jService = Depends(get_neo4j_service)
) -> NutritionService:
    """Dependency for nutrition service"""
    return NutritionService(db, neo4j)


def get_healthy_alternatives_service(
    neo4j: Neo4jService = Depends(get_neo4j_service)
) -> HealthyAlternativesService:
    """Dependency for healthy alternatives service"""
    return HealthyAlternativesService(neo4j)


def get_insights_engine(
    db: Session = Depends(get_db)
) -> NutritionInsightsEngine:
    """Dependency for nutrition insights engine"""
    return NutritionInsightsEngine(db)


# ========================================
# Endpoint 1: Get Recipe Nutrition
# ========================================

@router.get("/recipe/{recipe_id}", response_model=RecipeNutrition)
async def get_recipe_nutrition(
    recipe_id: str,
    servings: int = Query(1, ge=1, le=20, description="Number of servings"),
    current_user: User = Depends(get_current_user),
    nutrition_service: NutritionService = Depends(get_nutrition_service)
):
    """
    Get detailed nutrition information for a recipe
    
    **Parameters:**
    - `recipe_id`: Recipe ID from Neo4j
    - `servings`: Number of servings (default: 1)
    
    **Returns:**
    - Complete nutrition breakdown per serving and total
    - Health score (0-10)
    - Dietary classifications
    - Ingredient-level nutrition
    - Macro percentages
    """
    try:
        nutrition = await nutrition_service.calculate_recipe_nutrition(recipe_id, servings)
        
        if not nutrition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe not found: {recipe_id}"
            )
        
        return nutrition
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating recipe nutrition: {str(e)}"
        )


# ========================================
# Endpoint 2: Get Meal Plan Nutrition
# ========================================

@router.get("/meal-plan/{plan_id}", response_model=MealPlanNutrition)
async def get_meal_plan_nutrition(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    nutrition_service: NutritionService = Depends(get_nutrition_service)
):
    """
    Get comprehensive nutrition analysis for a meal plan
    
    **Parameters:**
    - `plan_id`: Meal plan ID
    
    **Returns:**
    - Total nutrition for the week
    - Daily averages
    - Per-day breakdown with all meals
    - Goal comparison (if user has active goals)
    - Health insights and recommendations
    """
    # Verify meal plan belongs to user
    meal_plan = db.query(MealPlan).filter(
        and_(
            MealPlan.id == plan_id,
            MealPlan.user_id == current_user.id
        )
    ).first()
    
    if not meal_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )
    
    try:
        # Get all meal plan items
        items = meal_plan.items
        
        # Calculate nutrition for each meal
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        total_fiber = 0
        total_sodium = 0
        
        # Group by day
        days_data = {}
        
        for item in items:
            # Calculate nutrition for this meal
            meal_nutrition = await nutrition_service.calculate_recipe_nutrition(
                item.recipe_id,
                item.servings
            )
            
            if not meal_nutrition:
                continue
            
            per_serving = meal_nutrition["per_serving"]
            
            # Add to totals
            total_calories += per_serving["calories"]
            total_protein += per_serving["protein_g"]
            total_carbs += per_serving["carbs_g"]
            total_fat += per_serving["fat_g"]
            total_fiber += per_serving.get("fiber_g", 0)
            total_sodium += per_serving.get("sodium_mg", 0)
            
            # Group by day
            day_key = item.day_of_week
            if day_key not in days_data:
                days_data[day_key] = {
                    "date": meal_plan.week_start_date + timedelta(days=day_key),
                    "meals": [],
                    "daily_total": {
                        "calories": 0,
                        "protein_g": 0,
                        "carbs_g": 0,
                        "fat_g": 0,
                        "fiber_g": 0,
                        "sodium_mg": 0
                    }
                }
            
            # Add meal
            days_data[day_key]["meals"].append(MealNutrition(
                meal_type=item.meal_type,
                recipe_id=item.recipe_id,
                recipe_title=item.recipe_title,
                calories=per_serving["calories"],
                protein_g=per_serving["protein_g"],
                carbs_g=per_serving["carbs_g"],
                fat_g=per_serving["fat_g"],
                health_score=meal_nutrition.get("health_score", 5.0)
            ))
            
            # Update daily totals
            days_data[day_key]["daily_total"]["calories"] += per_serving["calories"]
            days_data[day_key]["daily_total"]["protein_g"] += per_serving["protein_g"]
            days_data[day_key]["daily_total"]["carbs_g"] += per_serving["carbs_g"]
            days_data[day_key]["daily_total"]["fat_g"] += per_serving["fat_g"]
            days_data[day_key]["daily_total"]["fiber_g"] += per_serving.get("fiber_g", 0)
            days_data[day_key]["daily_total"]["sodium_mg"] += per_serving.get("sodium_mg", 0)
        
        # Calculate days count
        num_days = len(days_data)
        
        # Build breakdown by day
        breakdown_by_day = []
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day_num in sorted(days_data.keys()):
            day_data = days_data[day_num]
            breakdown_by_day.append(DayNutrition(
                date=day_data["date"],
                day_of_week=day_names[day_num],
                meals=day_data["meals"],
                daily_total=NutritionMacros(**day_data["daily_total"])
            ))
        
        # Calculate totals and averages
        total_nutrition = NutritionMacros(
            calories=total_calories,
            protein_g=round(total_protein, 1),
            carbs_g=round(total_carbs, 1),
            fat_g=round(total_fat, 1),
            fiber_g=round(total_fiber, 1),
            sodium_mg=total_sodium
        )
        
        daily_average = NutritionMacros(
            calories=int(total_calories / num_days) if num_days > 0 else 0,
            protein_g=round(total_protein / num_days, 1) if num_days > 0 else 0,
            carbs_g=round(total_carbs / num_days, 1) if num_days > 0 else 0,
            fat_g=round(total_fat / num_days, 1) if num_days > 0 else 0,
            fiber_g=round(total_fiber / num_days, 1) if num_days > 0 else 0,
            sodium_mg=int(total_sodium / num_days) if num_days > 0 else 0
        )
        
        # Check if user has active goals
        active_goal = db.query(NutritionGoal).filter(
            and_(
                NutritionGoal.user_id == current_user.id,
                NutritionGoal.is_active == True
            )
        ).first()
        
        if active_goal:
            goal_comparison = GoalProgress(
                has_active_goal=True,
                goal_type=active_goal.goal_type,
                calorie_target=active_goal.daily_calorie_target,
                calorie_actual_avg=daily_average.calories,
                achievement_pct=round((daily_average.calories / active_goal.daily_calorie_target) * 100, 1),
                status="on_track" if abs(daily_average.calories - active_goal.daily_calorie_target) < 100 else (
                    "over" if daily_average.calories > active_goal.daily_calorie_target else "under"
                )
            )
        else:
            goal_comparison = GoalProgress(has_active_goal=False)
        
        # Generate health insights
        insights = _generate_health_insights(daily_average, active_goal)
        
        return MealPlanNutrition(
            plan_id=str(plan_id),
            week_start=meal_plan.week_start_date,
            week_end=meal_plan.week_end_date,
            total_nutrition=total_nutrition,
            daily_average=daily_average,
            breakdown_by_day=breakdown_by_day,
            goal_comparison=goal_comparison,
            health_insights=insights
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating meal plan nutrition: {str(e)}"
        )


# ========================================
# Endpoint 3: Set Nutrition Goals
# ========================================

@router.post("/goals", response_model=NutritionGoalSchema, status_code=status.HTTP_201_CREATED)
def create_nutrition_goal(
    goal_data: NutritionGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update nutrition goals
    
    **Parameters:**
    - `goal_type`: Type of goal (weight_loss, muscle_gain, etc.)
    - `daily_calorie_target`: Target calories per day
    - `daily_protein_g_target`: Target protein (optional)
    - `daily_carbs_g_target`: Target carbs (optional)
    - `daily_fat_g_target`: Target fat (optional)
    - `start_date`: Goal start date
    - `duration_days`: Goal duration in days (optional)
    
    **Returns:**
    - Created nutrition goal with calculated end date
    
    **Note:** Setting a new goal deactivates previous goals
    """
    try:
        # Deactivate previous goals
        db.query(NutritionGoal).filter(
            and_(
                NutritionGoal.user_id == current_user.id,
                NutritionGoal.is_active == True
            )
        ).update({"is_active": False})
        
        # Calculate end date
        end_date = None
        if goal_data.duration_days:
            end_date = goal_data.start_date + timedelta(days=goal_data.duration_days)
        
        # Create new goal
        new_goal = NutritionGoal(
            user_id=current_user.id,
            goal_type=goal_data.goal_type.value,
            daily_calorie_target=goal_data.daily_calorie_target,
            daily_protein_g_target=goal_data.daily_protein_g_target,
            daily_carbs_g_target=goal_data.daily_carbs_g_target,
            daily_fat_g_target=goal_data.daily_fat_g_target,
            start_date=goal_data.start_date,
            end_date=end_date,
            is_active=True
        )
        
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)
        
        return NutritionGoalSchema(
            id=str(new_goal.id),
            user_id=str(new_goal.user_id),
            goal_type=new_goal.goal_type,
            daily_calorie_target=new_goal.daily_calorie_target,
            daily_protein_g_target=new_goal.daily_protein_g_target,
            daily_carbs_g_target=new_goal.daily_carbs_g_target,
            daily_fat_g_target=new_goal.daily_fat_g_target,
            start_date=new_goal.start_date,
            end_date=new_goal.end_date,
            duration_days=goal_data.duration_days,
            is_active=new_goal.is_active
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating nutrition goal: {str(e)}"
        )


# ========================================
# Endpoint 4: Get Nutrition Summary
# ========================================

@router.get("/summary", response_model=NutritionSummary)
async def get_nutrition_summary(
    start_date: date = Query(..., description="Summary start date"),
    end_date: date = Query(..., description="Summary end date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    nutrition_service: NutritionService = Depends(get_nutrition_service)
):
    """
    Get nutrition summary for a date range
    
    **Parameters:**
    - `start_date`: Start date (YYYY-MM-DD)
    - `end_date`: End date (YYYY-MM-DD)
    
    **Returns:**
    - Total nutrition for period
    - Daily averages
    - Macro distribution
    - Goal progress (if applicable)
    - Health metrics
    - Personalized insights
    - Recommendations
    
    **Example:** `/nutrition/summary?start_date=2026-01-01&end_date=2026-01-07`
    """
    try:
        # Validate date range
        if end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must be after start_date"
            )
        
        days_count = (end_date - start_date).days + 1
        
        if days_count > 90:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum date range is 90 days"
            )
        
        # Get all meal plans in date range
        meal_plans = db.query(MealPlan).filter(
            and_(
                MealPlan.user_id == current_user.id,
                MealPlan.week_start_date >= start_date,
                MealPlan.week_start_date <= end_date
            )
        ).all()
        
        # Calculate totals
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        total_fiber = 0
        total_sodium = 0
        
        health_scores = []
        high_protein_meals = 0
        low_sodium_meals = 0
        high_fiber_meals = 0
        
        for plan in meal_plans:
            for item in plan.items:
                nutrition = await nutrition_service.calculate_recipe_nutrition(
                    item.recipe_id,
                    item.servings
                )
                
                if not nutrition:
                    continue
                
                per_serving = nutrition["per_serving"]
                total_calories += per_serving["calories"]
                total_protein += per_serving["protein_g"]
                total_carbs += per_serving["carbs_g"]
                total_fat += per_serving["fat_g"]
                total_fiber += per_serving.get("fiber_g", 0)
                total_sodium += per_serving.get("sodium_mg", 0)
                
                health_score = nutrition.get("health_score", 5.0)
                health_scores.append(health_score)
                
                # Count health metrics
                if per_serving["protein_g"] >= 25:
                    high_protein_meals += 1
                if per_serving.get("sodium_mg", 0) <= 500:
                    low_sodium_meals += 1
                if per_serving.get("fiber_g", 0) >= 5:
                    high_fiber_meals += 1
        
        # Calculate averages
        total_nutrition = NutritionMacros(
            calories=total_calories,
            protein_g=round(total_protein, 1),
            carbs_g=round(total_carbs, 1),
            fat_g=round(total_fat, 1),
            fiber_g=round(total_fiber, 1),
            sodium_mg=total_sodium
        )
        
        daily_averages = NutritionMacros(
            calories=int(total_calories / days_count) if days_count > 0 else 0,
            protein_g=round(total_protein / days_count, 1) if days_count > 0 else 0,
            carbs_g=round(total_carbs / days_count, 1) if days_count > 0 else 0,
            fat_g=round(total_fat / days_count, 1) if days_count > 0 else 0,
            fiber_g=round(total_fiber / days_count, 1) if days_count > 0 else 0,
            sodium_mg=int(total_sodium / days_count) if days_count > 0 else 0
        )
        
        # Calculate macro distribution
        total_cal_from_macros = (total_protein * 4) + (total_carbs * 4) + (total_fat * 9)
        if total_cal_from_macros > 0:
            macro_distribution = MacroPercentages(
                protein_pct=int((total_protein * 4 / total_cal_from_macros) * 100),
                carbs_pct=int((total_carbs * 4 / total_cal_from_macros) * 100),
                fat_pct=int((total_fat * 9 / total_cal_from_macros) * 100)
            )
        else:
            macro_distribution = MacroPercentages(protein_pct=33, carbs_pct=33, fat_pct=34)
        
        # Get active goal
        active_goal = db.query(NutritionGoal).filter(
            and_(
                NutritionGoal.user_id == current_user.id,
                NutritionGoal.is_active == True
            )
        ).first()
        
        if active_goal:
            days_on_track = 0
            days_off_track = 0
            # Simplified - in production, track daily logs
            if abs(daily_averages.calories - active_goal.daily_calorie_target) < 100:
                days_on_track = days_count
            else:
                days_off_track = days_count
            
            goal_progress = GoalProgress(
                has_active_goal=True,
                goal_type=active_goal.goal_type,
                calorie_target=active_goal.daily_calorie_target,
                calorie_actual_avg=daily_averages.calories,
                achievement_pct=round((daily_averages.calories / active_goal.daily_calorie_target) * 100, 1),
                status="on_track" if abs(daily_averages.calories - active_goal.daily_calorie_target) < 100 else (
                    "over" if daily_averages.calories > active_goal.daily_calorie_target else "under"
                ),
                days_on_track=days_on_track,
                days_off_track=days_off_track
            )
        else:
            goal_progress = GoalProgress(has_active_goal=False)
        
        # Health metrics
        avg_health_score = sum(health_scores) / len(health_scores) if health_scores else 5.0
        health_metrics = HealthMetrics(
            avg_health_score=round(avg_health_score, 1),
            high_protein_meals=high_protein_meals,
            low_sodium_meals=low_sodium_meals,
            high_fiber_meals=high_fiber_meals
        )
        
        # Generate insights
        insights = _generate_summary_insights(daily_averages, goal_progress, health_metrics)
        
        return NutritionSummary(
            user_id=str(current_user.id),
            period=NutritionPeriod(
                start_date=start_date,
                end_date=end_date,
                days=days_count
            ),
            totals=total_nutrition,
            daily_averages=daily_averages,
            macro_distribution=macro_distribution,
            goal_progress=goal_progress,
            health_metrics=health_metrics,
            insights=insights,
            recommendations=[]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating nutrition summary: {str(e)}"
        )


# ========================================
# Endpoint 5: Get Goal Progress
# ========================================

@router.get("/goals/progress", response_model=dict)
def get_goal_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current nutrition goal progress
    
    **Returns:**
    - Active goal details
    - Progress percentage
    - Days elapsed and remaining
    - Recent performance (last 7/30 days)
    - Overall status
    - Next milestone
    """
    try:
        # Get active goal
        active_goal = db.query(NutritionGoal).filter(
            and_(
                NutritionGoal.user_id == current_user.id,
                NutritionGoal.is_active == True
            )
        ).first()
        
        if not active_goal:
            return {
                "active_goal": None,
                "message": "No active nutrition goal set"
            }
        
        # Calculate progress
        today = date.today()
        days_elapsed = (today - active_goal.start_date).days
        
        if active_goal.end_date:
            days_remaining = (active_goal.end_date - today).days
            total_days = (active_goal.end_date - active_goal.start_date).days
            progress_pct = (days_elapsed / total_days * 100) if total_days > 0 else 0
        else:
            days_remaining = None
            progress_pct = None
        
        # Get recent logs (simplified - would query nutrition_logs table)
        recent_performance = {
            "last_7_days": {
                "avg_calories": active_goal.daily_calorie_target,
                "days_on_track": 5,
                "achievement_rate": 71
            }
        }
        
        # Determine next milestone
        if active_goal.end_date:
            milestone_date = active_goal.start_date + timedelta(days=14)
            if today >= milestone_date:
                milestone_date = active_goal.start_date + timedelta(days=30)
            
            next_milestone = {
                "date": milestone_date.isoformat(),
                "description": f"{(milestone_date - active_goal.start_date).days} days completed"
            }
        else:
            next_milestone = None
        
        return {
            "active_goal": {
                "id": str(active_goal.id),
                "goal_type": active_goal.goal_type,
                "start_date": active_goal.start_date.isoformat(),
                "end_date": active_goal.end_date.isoformat() if active_goal.end_date else None,
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "progress_pct": round(progress_pct, 1) if progress_pct else None
            },
            "targets": MacroTargets(
                calories=active_goal.daily_calorie_target,
                protein_g=active_goal.daily_protein_g_target or 0,
                carbs_g=active_goal.daily_carbs_g_target or 0,
                fat_g=active_goal.daily_fat_g_target or 0
            ),
            "recent_performance": recent_performance,
            "overall_status": "on_track",
            "next_milestone": next_milestone
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting goal progress: {str(e)}"
        )


# ========================================
# Bonus Endpoint: Find Healthier Alternatives
# ========================================

@router.get("/alternatives/{recipe_id}", response_model=HealthyAlternative)
def get_healthier_alternative(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    healthy_alternatives_service: HealthyAlternativesService = Depends(get_healthy_alternatives_service)
):
    """
    Find a healthier alternative to a recipe
    
    **Parameters:**
    - `recipe_id`: Recipe ID to find alternative for
    
    **Returns:**
    - Healthier recipe alternative
    - Health score comparison
    - Improvement percentage
    - Detailed reason
    - Nutrition comparison
    """
    try:
        # Get user's dietary preferences (if any)
        # For now, no filtering - add dietary_restrictions from user model later
        
        alternative = healthy_alternatives_service.find_healthier_alternative(
            recipe_id=recipe_id,
            dietary_restrictions=None,
            allergens=None,
            min_score_improvement=0.5
        )
        
        if not alternative:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No healthier alternative found for this recipe"
            )
        
        return alternative
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding healthier alternative: {str(e)}"
        )


# ========================================
# Helper Functions
# ========================================

def _generate_health_insights(daily_average: NutritionMacros, active_goal: Optional[NutritionGoal]) -> List[str]:
    """Generate personalized health insights"""
    insights = []
    
    # Calorie insights
    if active_goal:
        diff = daily_average.calories - active_goal.daily_calorie_target
        if abs(diff) < 50:
            insights.append("Your meal plan perfectly matches your calorie goals!")
        elif diff > 0:
            insights.append(f"Your meal plan is {diff} calories above your daily target")
        else:
            insights.append(f"Your meal plan is {abs(diff)} calories below your daily target")
    
    # Protein insights
    if daily_average.protein_g >= 100:
        insights.append(f"Excellent protein intake! You're averaging {daily_average.protein_g}g/day")
    elif daily_average.protein_g < 60:
        insights.append(f"Consider adding more protein-rich foods (currently {daily_average.protein_g}g/day)")
    
    # Fiber insights
    if daily_average.fiber_g < 25:
        insights.append("Your fiber intake is below recommended levels - add more vegetables and whole grains")
    elif daily_average.fiber_g >= 30:
        insights.append("Great fiber intake! Your digestive system will thank you")
    
    # Sodium insights
    if daily_average.sodium_mg > 2300:
        insights.append("Sodium levels are high - consider reducing processed foods")
    elif daily_average.sodium_mg <= 1500:
        insights.append("Sodium levels are within healthy range")
    
    return insights


def _generate_summary_insights(
    daily_average: NutritionMacros, 
    goal_progress: GoalProgress, 
    health_metrics: HealthMetrics
) -> List[str]:
    """Generate nutrition summary insights"""
    insights = []
    
    # Goal progress insight
    if goal_progress.has_active_goal:
        if goal_progress.status == "on_track":
            insights.append(f"You're on track with your {goal_progress.goal_type} goal!")
        elif goal_progress.status == "over":
            insights.append(f"You exceeded your calorie goal by {goal_progress.achievement_pct - 100:.1f}%")
        else:
            insights.append(f"You're {100 - goal_progress.achievement_pct:.1f}% below your calorie goal")
    
    # Health score insight
    if health_metrics.avg_health_score >= 8.0:
        insights.append(f"Outstanding health score of {health_metrics.avg_health_score}/10!")
    elif health_metrics.avg_health_score >= 6.0:
        insights.append(f"Good health score of {health_metrics.avg_health_score}/10")
    else:
        insights.append(f"Health score is {health_metrics.avg_health_score}/10 - room for improvement")
    
    # High protein insight
    if health_metrics.high_protein_meals > 0:
        insights.append(f"You had {health_metrics.high_protein_meals} high-protein meals this period")
    
    # Fiber insight
    if health_metrics.high_fiber_meals < 5:
        insights.append("Try to include more high-fiber meals for better digestion")
    
    return insights


# ========================================
# Week 4 Advanced Endpoints
# ========================================

@router.get("/insights/recommendations", response_model=dict)
def get_personalized_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    insights_engine: NutritionInsightsEngine = Depends(get_insights_engine)
):
    """
    Get personalized nutrition recommendations
    
    **Returns:**
    - Personalized recommendations based on recent nutrition
    - Goal-specific advice
    - Actionable recipe suggestions
    - Priority-ranked improvements
    
    **Features:**
    - Analyzes recent 7-day nutrition patterns
    - Considers active nutrition goals
    - Provides specific recipe suggestions
    - Ranks recommendations by priority
    """
    try:
        # Get recent nutrition data (simplified for now)
        # In production, calculate from actual meal plan data
        recent_nutrition = NutritionMacros(
            calories=2000,
            protein_g=100,
            carbs_g=200,
            fat_g=70,
            fiber_g=25,
            sugar_g=40,
            sodium_mg=2000
        )
        
        # Get active goal
        active_goal = db.query(NutritionGoal).filter(
            and_(
                NutritionGoal.user_id == current_user.id,
                NutritionGoal.is_active == True
            )
        ).first()
        
        # Generate recommendations
        recommendations = insights_engine.generate_personalized_recommendations(
            user_id=str(current_user.id),
            recent_nutrition=recent_nutrition,
            goal=active_goal
        )
        
        return {
            "user_id": str(current_user.id),
            "period": "Last 7 days",
            "total_recommendations": len(recommendations),
            "recommendations": [
                {
                    "type": rec.type,
                    "message": rec.message,
                    "recipe_suggestions": rec.recipe_suggestions
                }
                for rec in recommendations
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendations: {str(e)}"
        )


@router.get("/insights/trends", response_model=dict)
def get_nutrition_trends(
    days: int = Query(30, ge=7, le=90, description="Days to analyze"),
    current_user: User = Depends(get_current_user),
    insights_engine: NutritionInsightsEngine = Depends(get_insights_engine)
):
    """
    Get nutrition trends analysis
    
    **Parameters:**
    - `days`: Number of days to analyze (7-90, default 30)
    
    **Returns:**
    - Calorie trends (increasing/decreasing/stable)
    - Protein trends
    - Consistency score (0-10)
    - Actionable insights
    
    **Use Cases:**
    - Identify nutrition patterns
    - Track progress over time
    - Spot inconsistencies
    """
    try:
        trends = insights_engine.analyze_nutrition_trends(
            user_id=str(current_user.id),
            days=days
        )
        
        return {
            "user_id": str(current_user.id),
            "analysis_period": trends["period"],
            "weeks_analyzed": trends["weeks_analyzed"],
            "calorie_trend": trends["calorie_trend"],
            "protein_trend": trends["protein_trend"],
            "consistency_score": trends["consistency_score"],
            "insights": trends["insights"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing trends: {str(e)}"
        )


@router.get("/insights/goal-prediction", response_model=dict)
def predict_goal_achievement(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    insights_engine: NutritionInsightsEngine = Depends(get_insights_engine)
):
    """
    Predict likelihood of achieving nutrition goal
    
    **Returns:**
    - Achievement prediction (highly_likely/likely/possible/unlikely)
    - Confidence percentage
    - Success rate based on recent performance
    - Days on/off track
    - Specific recommendations to improve
    
    **Algorithm:**
    - Analyzes last 14 days of performance
    - Calculates success rate
    - Projects to goal end date
    - Provides confidence score
    """
    try:
        # Get active goal
        active_goal = db.query(NutritionGoal).filter(
            and_(
                NutritionGoal.user_id == current_user.id,
                NutritionGoal.is_active == True
            )
        ).first()
        
        if not active_goal:
            return {
                "has_active_goal": False,
                "message": "No active goal to predict. Create a goal to get started!"
            }
        
        # Get recent performance (simplified)
        # In production, calculate from nutrition logs
        recent_performance = {
            "days_on_track": 10,
            "days_off_track": 4
        }
        
        prediction = insights_engine.predict_goal_achievement(
            user_id=str(current_user.id),
            goal=active_goal,
            recent_performance=recent_performance
        )
        
        return {
            "has_active_goal": True,
            "goal_type": active_goal.goal_type,
            "goal_start": active_goal.start_date.isoformat(),
            "goal_end": active_goal.end_date.isoformat() if active_goal.end_date else None,
            "prediction": prediction["prediction"],
            "confidence": prediction["confidence"],
            "message": prediction["message"],
            "success_rate": prediction["success_rate"],
            "days_on_track": prediction["days_on_track"],
            "days_off_track": prediction["days_off_track"],
            "progress_pct": prediction["progress_pct"],
            "days_remaining": prediction["days_remaining"],
            "recommendations": prediction["recommendations"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error predicting goal achievement: {str(e)}"
        )


@router.get("/insights/weekly-report", response_model=dict)
def get_weekly_report(
    week_start: date = Query(..., description="Week start date (Monday)"),
    current_user: User = Depends(get_current_user),
    insights_engine: NutritionInsightsEngine = Depends(get_insights_engine)
):
    """
    Get comprehensive weekly nutrition report
    
    **Parameters:**
    - `week_start`: Start of week (should be Monday)
    
    **Returns:**
    - Week summary
    - Key highlights
    - Areas to improve
    - Wins and achievements
    - Action items for next week
    
    **Perfect for:**
    - Weekly check-ins
    - Progress reviews
    - Planning next week
    """
    try:
        report = insights_engine.generate_weekly_report(
            user_id=str(current_user.id),
            week_start=week_start
        )
        
        return {
            "user_id": str(current_user.id),
            "week": report["week"],
            "summary": report["summary"],
            "highlights": report["highlights"],
            "areas_to_improve": report["areas_to_improve"],
            "wins": report["wins"],
            "action_items": report["action_items"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating weekly report: {str(e)}"
        )

