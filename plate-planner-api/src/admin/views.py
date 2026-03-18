from sqladmin import ModelView

from src.database.models import (
    User, UserPreferences, MealPlan, MealPlanItem,
    ShoppingList, ShoppingListItem, NutritionGoal, NutritionLog,
    UserPantryItem, IngredientNutrition, MealLogItem, UserMeal,
)


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"
    column_list = [
        User.id, User.email, User.full_name,
        User.is_active, User.is_premium, User.is_admin,
        User.auth_provider, User.onboarding_complete, User.created_at,
    ]
    column_searchable_list = [User.email, User.full_name]
    column_sortable_list = [User.email, User.created_at, User.is_active, User.is_premium]
    column_default_sort = ("created_at", True)
    form_excluded_columns = [
        User.hashed_password,
        User.preferences,
        User.meal_plans,
        User.shopping_lists,
        User.user_meals,
        User.pantry_items,
    ]
    can_create = False
    can_delete = False
    page_size = 25


class UserPreferencesAdmin(ModelView, model=UserPreferences):
    name = "User Preferences"
    name_plural = "User Preferences"
    icon = "fa-solid fa-sliders"
    column_list = [
        UserPreferences.id, UserPreferences.user_id,
        UserPreferences.dietary_restrictions, UserPreferences.allergies,
        UserPreferences.calorie_target, UserPreferences.people_count,
        UserPreferences.updated_at,
    ]
    can_create = False
    can_delete = False


class MealPlanAdmin(ModelView, model=MealPlan):
    name = "Meal Plan"
    name_plural = "Meal Plans"
    icon = "fa-solid fa-calendar-week"
    column_list = [
        MealPlan.id, MealPlan.user_id,
        MealPlan.week_start_date, MealPlan.week_end_date,
        MealPlan.status, MealPlan.total_calories,
        MealPlan.is_valid, MealPlan.created_at,
    ]
    column_sortable_list = [MealPlan.created_at, MealPlan.week_start_date, MealPlan.status]
    column_default_sort = ("created_at", True)
    can_create = False
    page_size = 25


class MealPlanItemAdmin(ModelView, model=MealPlanItem):
    name = "Meal Plan Item"
    name_plural = "Meal Plan Items"
    icon = "fa-solid fa-utensils"
    column_list = [
        MealPlanItem.id, MealPlanItem.plan_id,
        MealPlanItem.day_of_week, MealPlanItem.meal_type,
        MealPlanItem.recipe_title, MealPlanItem.calories,
        MealPlanItem.servings,
    ]
    column_searchable_list = [MealPlanItem.recipe_title]
    can_create = False
    can_delete = False


class ShoppingListAdmin(ModelView, model=ShoppingList):
    name = "Shopping List"
    name_plural = "Shopping Lists"
    icon = "fa-solid fa-cart-shopping"
    column_list = [
        ShoppingList.id, ShoppingList.user_id, ShoppingList.name,
        ShoppingList.status, ShoppingList.total_items,
        ShoppingList.purchased_items, ShoppingList.created_at,
    ]
    column_sortable_list = [ShoppingList.created_at, ShoppingList.status]
    can_create = False
    page_size = 25


class ShoppingListItemAdmin(ModelView, model=ShoppingListItem):
    name = "Shopping List Item"
    name_plural = "Shopping List Items"
    icon = "fa-solid fa-list-check"
    column_list = [
        ShoppingListItem.id, ShoppingListItem.list_id,
        ShoppingListItem.ingredient_name, ShoppingListItem.quantity,
        ShoppingListItem.unit, ShoppingListItem.category,
        ShoppingListItem.is_purchased,
    ]
    column_searchable_list = [ShoppingListItem.ingredient_name]
    can_create = False
    can_delete = False


class NutritionGoalAdmin(ModelView, model=NutritionGoal):
    name = "Nutrition Goal"
    name_plural = "Nutrition Goals"
    icon = "fa-solid fa-bullseye"
    column_list = [
        NutritionGoal.id, NutritionGoal.user_id,
        NutritionGoal.goal_type, NutritionGoal.daily_calorie_target,
        NutritionGoal.is_active, NutritionGoal.start_date,
    ]
    can_create = False


class NutritionLogAdmin(ModelView, model=NutritionLog):
    name = "Nutrition Log"
    name_plural = "Nutrition Logs"
    icon = "fa-solid fa-chart-line"
    column_list = [
        NutritionLog.id, NutritionLog.user_id,
        NutritionLog.log_date, NutritionLog.total_calories,
        NutritionLog.total_protein_g, NutritionLog.meals_count,
    ]
    column_sortable_list = [NutritionLog.log_date, NutritionLog.total_calories]
    column_default_sort = ("log_date", True)
    can_create = False
    can_delete = False


class UserPantryItemAdmin(ModelView, model=UserPantryItem):
    name = "Pantry Item"
    name_plural = "Pantry Items"
    icon = "fa-solid fa-jar"
    column_list = [
        UserPantryItem.id, UserPantryItem.user_id,
        UserPantryItem.item_name, UserPantryItem.created_at,
    ]
    column_searchable_list = [UserPantryItem.item_name]
    can_create = False
    can_delete = False


class IngredientNutritionAdmin(ModelView, model=IngredientNutrition):
    name = "Ingredient Nutrition"
    name_plural = "Ingredient Nutrition Cache"
    icon = "fa-solid fa-apple-whole"
    column_list = [
        IngredientNutrition.id, IngredientNutrition.ingredient_name,
        IngredientNutrition.calories, IngredientNutrition.protein_g,
        IngredientNutrition.carbs_g, IngredientNutrition.fat_g,
        IngredientNutrition.data_source,
    ]
    column_searchable_list = [IngredientNutrition.ingredient_name]
    column_sortable_list = [IngredientNutrition.ingredient_name, IngredientNutrition.calories]
    page_size = 50


class MealLogItemAdmin(ModelView, model=MealLogItem):
    name = "Meal Log Entry"
    name_plural = "Meal Log Entries"
    icon = "fa-solid fa-book"
    column_list = [
        MealLogItem.id, MealLogItem.user_id,
        MealLogItem.log_date, MealLogItem.meal_type,
        MealLogItem.description, MealLogItem.calories,
        MealLogItem.source,
    ]
    column_searchable_list = [MealLogItem.description]
    column_sortable_list = [MealLogItem.log_date, MealLogItem.calories]
    column_default_sort = ("log_date", True)
    can_create = False


class UserMealAdmin(ModelView, model=UserMeal):
    name = "User Meal"
    name_plural = "User Meals"
    icon = "fa-solid fa-camera"
    column_list = [
        UserMeal.id, UserMeal.user_id,
        UserMeal.meal_type, UserMeal.title,
        UserMeal.meal_date, UserMeal.calories,
        UserMeal.image_url,
    ]
    column_searchable_list = [UserMeal.title]
    column_sortable_list = [UserMeal.meal_date, UserMeal.calories]
    column_default_sort = ("meal_date", True)
    can_create = False
