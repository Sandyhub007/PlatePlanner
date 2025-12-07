from fastapi import APIRouter, Depends, HTTPException, Query, status
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



@router.get("/{plan_id}/items/{item_id}/alternatives", response_model=List[schemas.RecipeAlternative])
def get_item_alternatives(
    plan_id: str,
    item_id: str,
    limit: int = Query(5, ge=1, le=20),
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    try:
        return meal_plan_service.list_meal_plan_alternatives(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            item_id=item_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.put("/{plan_id}/items/{item_id}", response_model=schemas.MealPlan)
def swap_meal_item(
    plan_id: str,
    item_id: str,
    swap_request: schemas.MealPlanItemSwap,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    try:
        return meal_plan_service.swap_meal_plan_item(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            item_id=item_id,
            new_recipe_id=swap_request.new_recipe_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.post("/{plan_id}/regenerate", response_model=schemas.MealPlan)
def regenerate_plan(
    plan_id: str,
    regenerate_request: schemas.MealPlanRegenerateRequest,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    try:
        return meal_plan_service.regenerate_meal_plan_assignments(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            day_of_week=regenerate_request.day_of_week,
            preferences_override=regenerate_request.preferences_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.get("/{plan_id}/validation", response_model=schemas.MealPlanValidationResult)
def validate_plan(
    plan_id: str,
    refresh: bool = Query(False, description="Force re-run of validation before returning results."),
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db),
):
    try:
        return meal_plan_service.validate_meal_plan(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            refresh=refresh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc


@router.get("/{plan_id}/summary", response_model=schemas.MealPlanSummary)
def get_plan_summary(
    plan_id: str,
    refresh: bool = Query(False, description="Recompute and persist the summary before returning it."),
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db),
):
    try:
        return meal_plan_service.summarize_meal_plan(
            db=db,
            user_id=current_user.id,
            plan_id=plan_id,
            refresh=refresh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc
