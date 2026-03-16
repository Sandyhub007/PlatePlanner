"""
Advanced Nutrition Insights Engine
Generates personalized recommendations based on nutrition patterns and goals
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, timedelta, datetime
from collections import defaultdict
from sqlalchemy.orm import Session

from sqlalchemy import and_
from src.database.models import User, MealPlan, MealPlanItem, NutritionGoal, NutritionLog, MealLogItem
from src.schemas.nutrition import (
    NutritionRecommendation,
    NutritionMacros,
    GoalType,
    HealthMetrics,
)


class NutritionInsightsEngine:
    """
    Advanced insights engine for nutrition analysis
    Provides personalized recommendations and trend analysis
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_personalized_recommendations(
        self,
        user_id: str,
        recent_nutrition: NutritionMacros,
        goal: Optional[NutritionGoal] = None,
        health_metrics: Optional[HealthMetrics] = None
    ) -> List[NutritionRecommendation]:
        """
        Generate personalized nutrition recommendations
        
        Args:
            user_id: User ID
            recent_nutrition: Recent average nutrition
            goal: Active nutrition goal (if any)
            health_metrics: Recent health metrics
        
        Returns:
            List of personalized recommendations
        """
        recommendations = []
        
        # 1. Calorie-based recommendations
        if goal:
            calorie_recommendations = self._analyze_calorie_alignment(
                recent_nutrition.calories,
                goal.daily_calorie_target,
                goal.goal_type
            )
            recommendations.extend(calorie_recommendations)
        
        # 2. Macro balance recommendations
        macro_recommendations = self._analyze_macro_balance(recent_nutrition)
        recommendations.extend(macro_recommendations)
        
        # 3. Micronutrient recommendations
        micro_recommendations = self._analyze_micronutrients(recent_nutrition)
        recommendations.extend(micro_recommendations)
        
        # 4. Health score recommendations
        if health_metrics:
            health_recommendations = self._analyze_health_patterns(health_metrics)
            recommendations.extend(health_recommendations)
        
        # 5. Goal-specific recommendations
        if goal:
            goal_recommendations = self._generate_goal_specific_recommendations(
                goal,
                recent_nutrition
            )
            recommendations.extend(goal_recommendations)
        
        # Sort by priority and return top recommendations
        recommendations.sort(key=lambda x: self._recommendation_priority(x.type), reverse=True)
        return recommendations[:5]  # Top 5 recommendations
    
    def _analyze_calorie_alignment(
        self,
        actual_calories: int,
        target_calories: int,
        goal_type: str
    ) -> List[NutritionRecommendation]:
        """Analyze calorie alignment with goals"""
        recommendations = []
        
        diff = actual_calories - target_calories
        diff_pct = (diff / target_calories) * 100
        
        if abs(diff) < 50:
            # Perfect alignment
            recommendations.append(NutritionRecommendation(
                type="success",
                message=f"🎯 Perfect calorie alignment! You're hitting your {target_calories} kcal target.",
                recipe_suggestions=[]
            ))
        elif diff > 0:
            # Over target
            if diff_pct > 10:
                recommendations.append(NutritionRecommendation(
                    type="warning",
                    message=f"⚠️ You're {diff} calories over your daily target. Consider lighter meals or smaller portions.",
                    recipe_suggestions=["grilled_chicken_salad", "vegetable_stir_fry", "quinoa_bowl"]
                ))
        else:
            # Under target
            if abs(diff_pct) > 10:
                recommendations.append(NutritionRecommendation(
                    type="info",
                    message=f"📊 You're {abs(diff)} calories under target. For {goal_type}, consider adding nutrient-dense snacks.",
                    recipe_suggestions=["greek_yogurt_parfait", "mixed_nuts", "avocado_toast"]
                ))
        
        return recommendations
    
    def _analyze_macro_balance(self, nutrition: NutritionMacros) -> List[NutritionRecommendation]:
        """Analyze macronutrient balance"""
        recommendations = []
        
        # Calculate macro percentages
        total_cal_from_macros = (nutrition.protein_g * 4) + (nutrition.carbs_g * 4) + (nutrition.fat_g * 9)
        
        if total_cal_from_macros > 0:
            protein_pct = (nutrition.protein_g * 4 / total_cal_from_macros) * 100
            carbs_pct = (nutrition.carbs_g * 4 / total_cal_from_macros) * 100
            fat_pct = (nutrition.fat_g * 9 / total_cal_from_macros) * 100
            
            # Check protein
            if protein_pct < 15:
                recommendations.append(NutritionRecommendation(
                    type="warning",
                    message=f"💪 Low protein intake ({protein_pct:.0f}%). Aim for 20-30% of calories from protein.",
                    recipe_suggestions=["grilled_chicken_breast", "salmon_fillet", "lentil_curry", "tofu_scramble"]
                ))
            elif protein_pct > 35:
                recommendations.append(NutritionRecommendation(
                    type="info",
                    message=f"🥩 High protein intake ({protein_pct:.0f}%). Ensure adequate hydration and fiber.",
                    recipe_suggestions=["vegetable_soup", "fruit_smoothie", "whole_grain_pasta"]
                ))
            
            # Check carbs
            if carbs_pct < 25 and fat_pct < 40:
                # Likely energy deficiency
                recommendations.append(NutritionRecommendation(
                    type="info",
                    message="⚡ Low energy macros. Consider adding complex carbs for sustained energy.",
                    recipe_suggestions=["oatmeal", "sweet_potato", "brown_rice_bowl", "quinoa_salad"]
                ))
            
            # Check fat
            if fat_pct < 20:
                recommendations.append(NutritionRecommendation(
                    type="info",
                    message="🥑 Low fat intake. Healthy fats are essential for hormone health and nutrient absorption.",
                    recipe_suggestions=["avocado_salad", "salmon", "nuts_seeds_mix", "olive_oil_dressing"]
                ))
            elif fat_pct > 40:
                recommendations.append(NutritionRecommendation(
                    type="warning",
                    message=f"⚠️ High fat intake ({fat_pct:.0f}%). Consider balancing with more protein and carbs.",
                    recipe_suggestions=["lean_chicken", "egg_whites", "fruits", "vegetables"]
                ))
        
        return recommendations
    
    def _analyze_micronutrients(self, nutrition: NutritionMacros) -> List[NutritionRecommendation]:
        """Analyze micronutrient intake"""
        recommendations = []
        
        # Fiber
        if nutrition.fiber_g < 20:
            recommendations.append(NutritionRecommendation(
                type="warning",
                message=f"🌾 Low fiber intake ({nutrition.fiber_g}g/day). Aim for 25-35g for digestive health.",
                recipe_suggestions=["black_bean_bowl", "broccoli_salad", "oatmeal", "lentil_soup"]
            ))
        elif nutrition.fiber_g >= 30:
            recommendations.append(NutritionRecommendation(
                type="success",
                message=f"✅ Excellent fiber intake ({nutrition.fiber_g}g/day)! Great for digestive health.",
                recipe_suggestions=[]
            ))
        
        # Sodium
        if nutrition.sodium_mg > 2300:
            recommendations.append(NutritionRecommendation(
                type="warning",
                message=f"🧂 High sodium intake ({nutrition.sodium_mg}mg/day). Limit to 2,300mg to protect heart health.",
                recipe_suggestions=["fresh_salad", "grilled_vegetables", "herb_seasoned_chicken", "homemade_meals"]
            ))
        
        # Sugar
        if nutrition.sugar_g > 50:
            recommendations.append(NutritionRecommendation(
                type="warning",
                message=f"🍬 High sugar intake ({nutrition.sugar_g}g/day). Consider reducing added sugars.",
                recipe_suggestions=["greek_yogurt_unsweetened", "fresh_berries", "herbal_tea", "dark_chocolate"]
            ))
        
        return recommendations
    
    def _analyze_health_patterns(self, health_metrics: HealthMetrics) -> List[NutritionRecommendation]:
        """Analyze health score patterns"""
        recommendations = []
        
        if health_metrics.avg_health_score < 5.0:
            recommendations.append(NutritionRecommendation(
                type="alert",
                message=f"🚨 Health score is low ({health_metrics.avg_health_score}/10). Focus on whole foods and balanced meals.",
                recipe_suggestions=["mediterranean_salad", "grilled_fish", "vegetable_soup", "fruit_bowl"]
            ))
        elif health_metrics.avg_health_score >= 8.0:
            recommendations.append(NutritionRecommendation(
                type="success",
                message=f"🌟 Outstanding health score ({health_metrics.avg_health_score}/10)! Keep up the great work!",
                recipe_suggestions=[]
            ))
        
        if health_metrics.high_protein_meals < 5:
            recommendations.append(NutritionRecommendation(
                type="info",
                message="💪 Try to include more high-protein meals (25g+ per meal) for muscle maintenance.",
                recipe_suggestions=["chicken_breast", "salmon", "greek_yogurt", "protein_smoothie"]
            ))
        
        if health_metrics.low_sodium_meals < 7:
            recommendations.append(NutritionRecommendation(
                type="info",
                message="🧂 Most meals are high in sodium. Focus on fresh, whole ingredients and herbs for flavor.",
                recipe_suggestions=["fresh_salads", "grilled_meats", "roasted_vegetables", "fruit_snacks"]
            ))
        
        return recommendations
    
    def _generate_goal_specific_recommendations(
        self,
        goal: NutritionGoal,
        recent_nutrition: NutritionMacros
    ) -> List[NutritionRecommendation]:
        """Generate recommendations specific to user's goal"""
        recommendations = []
        
        if goal.goal_type == "weight_loss":
            # Weight loss recommendations
            if recent_nutrition.protein_g < 100:
                recommendations.append(NutritionRecommendation(
                    type="info",
                    message="🎯 For weight loss, aim for 1g protein per lb body weight to preserve muscle mass.",
                    recipe_suggestions=["lean_chicken", "fish", "egg_whites", "low_fat_greek_yogurt"]
                ))
            
            if recent_nutrition.fiber_g < 25:
                recommendations.append(NutritionRecommendation(
                    type="info",
                    message="💡 High-fiber foods increase satiety and support weight loss.",
                    recipe_suggestions=["vegetable_soup", "salad", "beans", "whole_grains"]
                ))
        
        elif goal.goal_type == "muscle_gain":
            # Muscle gain recommendations
            if recent_nutrition.protein_g < 150:
                recommendations.append(NutritionRecommendation(
                    type="warning",
                    message="💪 For muscle gain, target 1.2-1.6g protein per lb body weight.",
                    recipe_suggestions=["steak", "chicken_breast", "protein_shake", "eggs"]
                ))
            
            if recent_nutrition.calories < goal.daily_calorie_target:
                recommendations.append(NutritionRecommendation(
                    type="warning",
                    message="📈 Muscle gain requires a calorie surplus. Add nutrient-dense foods.",
                    recipe_suggestions=["pasta", "rice", "avocado", "nuts", "salmon"]
                ))
        
        elif goal.goal_type == "athletic_performance":
            # Athletic performance recommendations
            carb_pct = (recent_nutrition.carbs_g * 4 / recent_nutrition.calories) * 100
            
            if carb_pct < 45:
                recommendations.append(NutritionRecommendation(
                    type="info",
                    message="⚡ Athletes need 45-65% calories from carbs for optimal performance.",
                    recipe_suggestions=["oatmeal", "sweet_potato", "pasta", "rice", "bananas"]
                ))
        
        return recommendations
    
    def _recommendation_priority(self, rec_type: str) -> int:
        """Determine recommendation priority"""
        priority_map = {
            "alert": 5,
            "warning": 4,
            "info": 3,
            "success": 2,
            "tip": 1
        }
        return priority_map.get(rec_type, 0)
    
    def analyze_nutrition_trends(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze nutrition trends over time using real NutritionLog data.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Trend analysis with patterns and predictions
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Query real daily nutrition logs
        logs = self.db.query(NutritionLog).filter(
            and_(
                NutritionLog.user_id == user_id,
                NutritionLog.log_date >= start_date,
                NutritionLog.log_date <= end_date,
            )
        ).order_by(NutritionLog.log_date).all()

        # Group logs by ISO week
        weekly_data: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            "calories": [],
            "protein": [],
            "carbs": [],
            "fat": [],
        })

        for log in logs:
            week_key = log.log_date.isocalendar()[1]
            weekly_data[week_key]["calories"].append(log.total_calories or 0)
            weekly_data[week_key]["protein"].append(log.total_protein_g or 0)
            weekly_data[week_key]["carbs"].append(log.total_carbs_g or 0)
            weekly_data[week_key]["fat"].append(log.total_fat_g or 0)

        # Calculate weekly averages in chronological order
        sorted_weeks = sorted(weekly_data.keys())
        weekly_avg_calories = []
        weekly_avg_protein = []

        for wk in sorted_weeks:
            data = weekly_data[wk]
            weekly_avg_calories.append(
                int(sum(data["calories"]) / len(data["calories"])) if data["calories"] else 0
            )
            weekly_avg_protein.append(
                round(sum(data["protein"]) / len(data["protein"]), 1) if data["protein"] else 0
            )

        # Determine trend direction from weekly averages
        def _compute_trend(values: List) -> str:
            if len(values) < 2:
                return "stable"
            first_half = sum(values[: len(values) // 2]) / max(len(values) // 2, 1)
            second_half = sum(values[len(values) // 2 :]) / max(len(values) - len(values) // 2, 1)
            if first_half == 0:
                return "stable"
            pct_change = ((second_half - first_half) / first_half) * 100
            if pct_change > 5:
                return "increasing"
            elif pct_change < -5:
                return "decreasing"
            return "stable"

        calorie_trend = _compute_trend(weekly_avg_calories)
        protein_trend = _compute_trend(weekly_avg_protein)

        # Consistency score: fraction of days that have log entries, scaled to 0-10
        expected_days = days
        logged_days = len(logs)
        consistency_score = round(min((logged_days / expected_days) * 10, 10), 1)

        # Build insights
        insights: List[str] = []

        if len(sorted_weeks) >= 3:
            insights.append(f"Analyzed {len(sorted_weeks)} weeks of nutrition data ({logged_days} logged days)")
        else:
            insights.append(f"Only {logged_days} days of data available. Log meals consistently for better trends (need 3+ weeks)")

        if calorie_trend == "increasing":
            insights.append("Calorie intake is trending upward over the period")
        elif calorie_trend == "decreasing":
            insights.append("Calorie intake is trending downward over the period")
        else:
            insights.append("Calorie intake has been relatively stable")

        if protein_trend == "increasing":
            insights.append("Protein intake is improving over time")
        elif protein_trend == "decreasing":
            insights.append("Protein intake is declining - consider adding protein-rich foods")

        if consistency_score >= 8:
            insights.append("Excellent logging consistency! Keep it up")
        elif consistency_score < 4:
            insights.append("Low logging consistency. Try to log meals daily for accurate insights")

        return {
            "period": f"{days} days",
            "weeks_analyzed": len(sorted_weeks),
            "logged_days": logged_days,
            "calorie_trend": calorie_trend,
            "protein_trend": protein_trend,
            "consistency_score": consistency_score,
            "weekly_avg_calories": weekly_avg_calories,
            "weekly_avg_protein": weekly_avg_protein,
            "insights": insights,
        }
    
    def predict_goal_achievement(
        self,
        user_id: str,
        goal: NutritionGoal,
        recent_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Predict likelihood of achieving nutrition goal
        
        Args:
            user_id: User ID
            goal: Active nutrition goal
            recent_performance: Recent performance metrics
        
        Returns:
            Achievement prediction with confidence and recommendations
        """
        # Calculate days on track vs off track
        days_on_track = recent_performance.get("days_on_track", 0)
        days_off_track = recent_performance.get("days_off_track", 0)
        total_days = days_on_track + days_off_track
        
        if total_days == 0:
            return {
                "prediction": "insufficient_data",
                "confidence": 0,
                "message": "Need at least 7 days of data for prediction"
            }
        
        # Calculate success rate
        success_rate = days_on_track / total_days if total_days > 0 else 0
        
        # Determine prediction
        if success_rate >= 0.8:
            prediction = "highly_likely"
            confidence = 90
            message = "🎯 You're on track to achieve your goal! Maintain current habits."
        elif success_rate >= 0.6:
            prediction = "likely"
            confidence = 70
            message = "👍 Good progress! A few adjustments will put you on track."
        elif success_rate >= 0.4:
            prediction = "possible"
            confidence = 50
            message = "⚠️ Inconsistent progress. Focus on building consistent habits."
        else:
            prediction = "unlikely"
            confidence = 30
            message = "🚨 Current pace unlikely to achieve goal. Consider adjusting targets or habits."
        
        # Calculate estimated completion
        days_elapsed = (date.today() - goal.start_date).days
        if goal.end_date:
            days_total = (goal.end_date - goal.start_date).days
            days_remaining = (goal.end_date - date.today()).days
            progress_pct = (days_elapsed / days_total) * 100 if days_total > 0 else 0
        else:
            days_total = None
            days_remaining = None
            progress_pct = None
        
        return {
            "prediction": prediction,
            "confidence": confidence,
            "message": message,
            "success_rate": round(success_rate * 100, 1),
            "days_on_track": days_on_track,
            "days_off_track": days_off_track,
            "progress_pct": progress_pct,
            "days_remaining": days_remaining,
            "recommendations": self._generate_achievement_recommendations(
                prediction,
                goal,
                success_rate
            )
        }
    
    def _generate_achievement_recommendations(
        self,
        prediction: str,
        goal: NutritionGoal,
        success_rate: float
    ) -> List[str]:
        """Generate recommendations to improve goal achievement"""
        recommendations = []
        
        if prediction == "unlikely":
            recommendations.append("Consider revising your calorie target to a more sustainable level")
            recommendations.append("Focus on 1-2 small habit changes instead of overhauling everything")
            recommendations.append("Track meals consistently to identify patterns")
        elif prediction == "possible":
            recommendations.append("Meal prep on weekends to ensure you have healthy options ready")
            recommendations.append("Set daily reminders to track your nutrition")
            recommendations.append("Find 2-3 go-to healthy meals you enjoy")
        elif prediction == "likely":
            recommendations.append("Keep doing what you're doing!")
            recommendations.append("Plan for challenging situations (travel, dining out)")
            recommendations.append("Celebrate small wins to maintain motivation")
        else:
            recommendations.append("Excellent consistency! Consider setting a new challenge")
            recommendations.append("Share your success strategies with others")
            recommendations.append("Focus on maintaining these healthy habits long-term")
        
        return recommendations
    
    def generate_weekly_report(
        self,
        user_id: str,
        week_start: date
    ) -> Dict[str, Any]:
        """
        Generate comprehensive weekly nutrition report using real log data.

        Args:
            user_id: User ID
            week_start: Start of week

        Returns:
            Weekly report with analysis and recommendations
        """
        week_end = week_start + timedelta(days=6)

        # Get nutrition logs for the week
        logs = self.db.query(NutritionLog).filter(
            and_(
                NutritionLog.user_id == user_id,
                NutritionLog.log_date >= week_start,
                NutritionLog.log_date <= week_end,
            )
        ).order_by(NutritionLog.log_date).all()

        # Get meal plan (if any)
        meal_plans = self.db.query(MealPlan).filter(
            and_(
                MealPlan.user_id == user_id,
                MealPlan.week_start_date == week_start,
            )
        ).all()

        # Get active goal
        active_goal = self.db.query(NutritionGoal).filter(
            and_(
                NutritionGoal.user_id == user_id,
                NutritionGoal.is_active == True,
            )
        ).first()

        highlights: List[str] = []
        areas_to_improve: List[str] = []
        wins: List[str] = []
        action_items: List[str] = []

        # Meal plan analysis
        if meal_plans:
            highlights.append("Meal plan created for the week")
            wins.append("Proactive meal planning")
        else:
            areas_to_improve.append("No meal plan for this week")
            action_items.append("Create a meal plan for next week")

        # Logging consistency
        logged_days = len(logs)
        if logged_days >= 6:
            highlights.append(f"Logged meals on {logged_days}/7 days - excellent consistency!")
            wins.append("Consistent meal logging")
        elif logged_days >= 4:
            highlights.append(f"Logged meals on {logged_days}/7 days")
            action_items.append("Try logging meals every day for a complete picture")
        else:
            areas_to_improve.append(f"Only {logged_days}/7 days logged")
            action_items.append("Set a daily reminder to log your meals")

        # Nutrition analysis
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        total_fiber = 0
        days_on_track = 0

        daily_data: List[Dict[str, Any]] = []

        for log in logs:
            cal = log.total_calories or 0
            prot = log.total_protein_g or 0
            carbs = log.total_carbs_g or 0
            fat = log.total_fat_g or 0
            fib = log.total_fiber_g or 0

            total_calories += cal
            total_protein += prot
            total_carbs += carbs
            total_fat += fat
            total_fiber += fib

            daily_data.append({
                "date": log.log_date.isoformat(),
                "calories": cal,
                "protein_g": prot,
                "carbs_g": carbs,
                "fat_g": fat,
                "meals_count": log.meals_count or 0,
            })

            if active_goal and cal > 0 and abs(cal - active_goal.daily_calorie_target) <= 200:
                days_on_track += 1

        if logged_days > 0:
            avg_cal = int(total_calories / logged_days)
            avg_protein = round(total_protein / logged_days, 1)
            avg_fiber = round(total_fiber / logged_days, 1)

            highlights.append(f"Average daily intake: {avg_cal} kcal, {avg_protein}g protein")

            if avg_protein >= 100:
                wins.append(f"Strong protein intake averaging {avg_protein}g/day")
            elif avg_protein < 60:
                areas_to_improve.append(f"Low protein intake ({avg_protein}g/day) - aim for 100g+")
                action_items.append("Add protein-rich foods like chicken, fish, eggs, or legumes")

            if avg_fiber >= 25:
                wins.append(f"Good fiber intake averaging {avg_fiber}g/day")
            elif avg_fiber < 15:
                areas_to_improve.append(f"Low fiber intake ({avg_fiber}g/day)")
                action_items.append("Add more vegetables, fruits, and whole grains")

            # Goal tracking
            if active_goal:
                target = active_goal.daily_calorie_target
                diff = avg_cal - target
                if abs(diff) <= 100:
                    wins.append(f"On target with calorie goal ({target} kcal)")
                elif diff > 100:
                    areas_to_improve.append(f"Exceeded calorie target by ~{diff} kcal/day")
                    action_items.append("Consider lighter meals or smaller portions")
                else:
                    areas_to_improve.append(f"Under calorie target by ~{abs(diff)} kcal/day")
                    action_items.append("Add nutrient-dense snacks to meet your target")

                highlights.append(f"{days_on_track}/{logged_days} days on track with calorie goal")

        summary = f"Week of {week_start} to {week_end}: {logged_days} days logged, {total_calories} total calories"

        return {
            "week": f"{week_start} to {week_end}",
            "summary": summary,
            "logged_days": logged_days,
            "total_calories": total_calories,
            "avg_daily_calories": int(total_calories / logged_days) if logged_days > 0 else 0,
            "daily_data": daily_data,
            "highlights": highlights,
            "areas_to_improve": areas_to_improve,
            "wins": wins,
            "action_items": action_items,
        }

