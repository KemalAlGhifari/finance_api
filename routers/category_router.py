# routers/category_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models, schemas
from auth import get_current_user, get_db
from typing import List

router = APIRouter(prefix="/categories", tags=["categories"])

@router.post("/", response_model=schemas.CategoryResponse)
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    cat = models.Category(user_id=current_user.id, name=payload.name, type=payload.type)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.get("/", response_model=List[schemas.CategoryResponse])
def list_categories(type: schemas.CategoryType | None = Query(None), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Category).filter(models.Category.user_id == current_user.id)
    if type:
        q = q.filter(models.Category.type == type)
    return q.all()

@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    cat = db.query(models.Category).filter(models.Category.id==category_id, models.Category.user_id==current_user.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()
    return {"detail": "deleted"}
