from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.database import session, models
from src.schemas import meal_plan as schemas
from src.auth import security
from src.services import meal_plan_service

router = APIRouter(
    prefix="/meal-plans",
    tags=["meal-plans"],
)

@router.post("/generate", response_model=schemas.MealPlan)
def generate_meal_plan(
    plan_request: schemas.MealPlanCreate,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    try:
        meal_plan = meal_plan_service.generate_meal_plan(
            db=db,
            user_id=current_user.id,
            week_start_date=plan_request.week_start_date,
            preferences_override=plan_request.preferences_override,
        )
        return meal_plan
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc

@router.get("/", response_model=List[schemas.MealPlan])
def get_my_meal_plans(
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    return meal_plan_service.get_user_meal_plans(db, current_user.id)

@router.get("/{plan_id}", response_model=schemas.MealPlan)
def get_meal_plan(
    plan_id: str,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    meal_plan = meal_plan_service.get_meal_plan(db, plan_id)
    if not meal_plan:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    if meal_plan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this plan")
    return meal_plan

