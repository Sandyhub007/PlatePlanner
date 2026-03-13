from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import session, models
from src.schemas import user as schemas
from src.auth import security

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(security.get_current_active_user)
):
    return current_user

@router.put("/me", response_model=schemas.User)
def update_user_profile(
    update_data: schemas.UserUpdate,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    data = update_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/me/preferences", response_model=schemas.UserPreferences)
def update_user_preferences(
    preferences: schemas.UserPreferencesUpdate,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    db_prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == current_user.id).first()
    if not db_prefs:
        # Should have been created on registration, but just in case
        db_prefs = models.UserPreferences(user_id=current_user.id)
        db.add(db_prefs)

    # Update fields
    update_data = preferences.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_prefs, key, value)

    db.commit()
    db.refresh(db_prefs)
    return db_prefs

@router.get("/me/preferences", response_model=schemas.UserPreferences)
def get_user_preferences(
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    db_prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == current_user.id).first()
    if not db_prefs:
         # Should have been created on registration, but just in case
        db_prefs = models.UserPreferences(user_id=current_user.id)
        db.add(db_prefs)
        db.commit()
        db.refresh(db_prefs)
    return db_prefs


@router.post("/me/onboarding", response_model=schemas.User)
def complete_onboarding(
    onboarding: schemas.OnboardingRequest,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db),
):
    """
    Save all onboarding preferences in one call and mark the user as onboarded.

    Accepts goal_type, calorie_target, dietary_restrictions, cuisine_preferences,
    allergies, and other nutritional targets. Creates or updates UserPreferences
    and sets ``onboarding_complete = True`` on the User row.
    """
    # Upsert preferences
    db_prefs = (
        db.query(models.UserPreferences)
        .filter(models.UserPreferences.user_id == current_user.id)
        .first()
    )
    if not db_prefs:
        db_prefs = models.UserPreferences(user_id=current_user.id)
        db.add(db_prefs)

    # Map onboarding fields to preferences columns
    pref_fields = {
        "dietary_restrictions": onboarding.dietary_restrictions,
        "allergies": onboarding.allergies,
        "cuisine_preferences": onboarding.cuisine_preferences,
        "calorie_target": onboarding.calorie_target,
        "protein_target": onboarding.protein_target,
        "carb_target": onboarding.carb_target,
        "fat_target": onboarding.fat_target,
        "cooking_time_max": onboarding.cooking_time_max,
        "budget_per_week": onboarding.budget_per_week,
        "people_count": onboarding.people_count,
    }
    for key, value in pref_fields.items():
        if value is not None:
            setattr(db_prefs, key, value)

    # Optionally store goal_type as a NutritionGoal if provided
    if onboarding.goal_type and onboarding.calorie_target:
        from datetime import date as _date
        existing_goal = (
            db.query(models.NutritionGoal)
            .filter(
                models.NutritionGoal.user_id == current_user.id,
                models.NutritionGoal.is_active == True,
            )
            .first()
        )
        if existing_goal:
            existing_goal.goal_type = onboarding.goal_type
            existing_goal.daily_calorie_target = onboarding.calorie_target
            existing_goal.daily_protein_g_target = onboarding.protein_target
            existing_goal.daily_carbs_g_target = onboarding.carb_target
            existing_goal.daily_fat_g_target = onboarding.fat_target
        else:
            goal = models.NutritionGoal(
                user_id=current_user.id,
                goal_type=onboarding.goal_type,
                daily_calorie_target=onboarding.calorie_target,
                daily_protein_g_target=onboarding.protein_target,
                daily_carbs_g_target=onboarding.carb_target,
                daily_fat_g_target=onboarding.fat_target,
                start_date=_date.today(),
                is_active=True,
            )
            db.add(goal)

    # Mark onboarding complete
    current_user.onboarding_complete = True
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

