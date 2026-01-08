# routers/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas, auth
from auth import get_db, hash_password, verify_password, create_access_token
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserResponse)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create default categories for new user
    default_categories = [
        # Income categories
        {"name": "Gaji", "type": "income"},
        {"name": "Bonus", "type": "income"},
        {"name": "Bisnis", "type": "income"},
        {"name": "Side Job / Freelance", "type": "income"},
        {"name": "Investasi", "type": "income"},
        {"name": "Lainnya", "type": "income"},
        # Expense categories
        {"name": "Makanan", "type": "expense"},
        {"name": "Transport", "type": "expense"},
        {"name": "Belanja Bulanan", "type": "expense"},
        {"name": "Tagihan (Listrik, Air, Internet)", "type": "expense"},
        {"name": "Cicilan", "type": "expense"},
        {"name": "Lainnya", "type": "expense"},
    ]
    
    for cat_data in default_categories:
        category = models.Category(
            user_id=user.id,
            name=cat_data["name"],
            type=models.CategoryType[cat_data["type"]]
        )
        db.add(category)
    
    db.commit()
    
    return user

@router.post("/login", response_model=schemas.Token)
def login(form_data: dict, db: Session = Depends(get_db)):
    # form_data may come as JSON { "email": "...", "password": "..." }
    email = form_data.get("email")
    password = form_data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(days=7))
    return {"access_token": access_token, "token_type": "bearer"}
