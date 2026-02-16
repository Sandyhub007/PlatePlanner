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

