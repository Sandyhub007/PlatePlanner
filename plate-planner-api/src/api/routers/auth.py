from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.database import session, models
from src.schemas import user as schemas
from src.auth import security
from src.config.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)

@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(session.get_db)):
    # Check if user already exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = security.get_password_hash(user.password)
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Initialize empty preferences
    preferences = models.UserPreferences(user_id=new_user.id)
    db.add(preferences)
    db.commit()
    
    return new_user

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(session.get_db)
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

@router.post("/google", response_model=schemas.Token)
def google_login(
    login_request: schemas.GoogleLoginRequest,
    db: Session = Depends(session.get_db)
):
    email = None
    full_name_val = None
    photo_url = None

    # 1. Try verifiable ID Token first
    if login_request.id_token:
        try:
            # Verify the token
            # Note: In production, specify the CLIENT_ID as the audience
            id_info = id_token.verify_oauth2_token(
                login_request.id_token, 
                google_requests.Request(), 
                clock_skew_in_seconds=10
            )
            email = id_info.get("email")
            full_name_val = id_info.get("name")
            photo_url = id_info.get("picture")
        except ValueError as e:
            # If ID token is invalid, log it but checkout access_token
            print(f"ID Token validation failed: {e}")
            pass

    # 2. Fallback to Access Token if Email not found yet
    if not email and login_request.access_token:
        try:
            with httpx.Client() as client:
                resp = client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo", 
                    headers={"Authorization": f"Bearer {login_request.access_token}"},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email")
                    full_name_val = data.get("name")
                    photo_url = data.get("picture")
        except Exception as e:
            print(f"Access Token validation failed: {e}")

    if not email:
        raise HTTPException(status_code=400, detail="Invalid Google credentials. Could not verify email.")

    # Check if user exists
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        # Create a new user
        import secrets
        random_password = secrets.token_urlsafe(32)
        hashed_password = security.get_password_hash(random_password)
        
        user = models.User(
            email=email,
            hashed_password=hashed_password, 
            full_name=full_name_val or split_name_from_email(email),
            is_active=True,
            auth_provider="google",
            profile_photo_url=photo_url
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Initialize preferences
        preferences = models.UserPreferences(user_id=user.id)
        db.add(preferences)
        db.commit()
    else:
        # Update photo URL if we have a new one  
        if photo_url and user.profile_photo_url != photo_url:
            user.profile_photo_url = photo_url
            db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

def split_name_from_email(email: str) -> str:
    return email.split("@")[0].capitalize()

