from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
import httpx
import os
import uuid
import logging
from datetime import date
from pathlib import Path

from src.database import session, models
from src.schemas import user_meal as schemas
from src.auth import security

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user-meals",
    tags=["user_meals"],
)

import asyncio

# Local upload directory (fallback when Vercel Blob is not configured)
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "user_meals"


async def upload_file(filename: str, content: bytes, content_type: str) -> str:
    """Upload to Vercel Blob if configured, otherwise store locally."""
    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")

    if blob_token:
        try:
            import vercel_blob

            def _upload():
                resp = vercel_blob.put(
                    filename,
                    content,
                    options={"access": "public", "token": blob_token},
                )
                return resp.get("url")

            url = await asyncio.to_thread(_upload)
            return url
        except Exception as e:
            logger.warning(f"Vercel Blob upload failed, falling back to local storage: {e}")

    # Fallback: save to local filesystem and return a relative URL
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / filename.replace("/", "_")
    dest.write_bytes(content)
    return f"/uploads/user_meals/{dest.name}"

@router.post("/upload", response_model=schemas.UserMealResponse)
async def upload_meal_photo(
    file: UploadFile = File(...),
    meal_type: str = Form(...),
    meal_date: date = Form(...),
    title: Optional[str] = Form(None),
    calories: Optional[int] = Form(None),
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """
    Upload a photo of a meal to Vercel Blob Storage and record it in the database.
    """
    if not file.content_type.startswith("image/"):
         raise HTTPException(status_code=400, detail="File must be an image.")
         
    content = await file.read()
    
    # Generate unique filename securely to avoid overwrites
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    unique_filename = f"user_meals/{current_user.id}/{uuid.uuid4().hex}.{ext}"
    
    try:
        image_url = await upload_file(unique_filename, content, file.content_type)
    except Exception as e:
        logger.exception("File upload failed")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
    
    # Save to database
    db_meal = models.UserMeal(
        user_id=current_user.id,
        meal_type=meal_type,
        image_url=image_url,
        meal_date=meal_date,
        title=title,
        calories=calories
    )
    db.add(db_meal)
    db.commit()
    db.refresh(db_meal)
    
    return db_meal

@router.get("/", response_model=List[schemas.UserMealResponse])
def get_user_meals(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: models.User = Depends(security.get_current_active_user),
    db: Session = Depends(session.get_db)
):
    """
    Get all meals uploaded by the current user, optionally filtered by date range.
    """
    query = db.query(models.UserMeal).filter(models.UserMeal.user_id == current_user.id)
    
    if start_date:
        query = query.filter(models.UserMeal.meal_date >= start_date)
    if end_date:
        query = query.filter(models.UserMeal.meal_date <= end_date)
        
    return query.order_by(models.UserMeal.meal_date.desc(), models.UserMeal.created_at.desc()).all()
