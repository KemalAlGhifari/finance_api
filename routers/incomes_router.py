# routers/incomes_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from auth import get_db, get_current_user

router = APIRouter(prefix="/incomes", tags=["incomes"])

@router.post("/", response_model=schemas.TransactionResponse)
def create_income(payload: schemas.IncomeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # optional category validation ownership
    if payload.category_id:
        cat = db.query(models.Category).filter(models.Category.id==payload.category_id, models.Category.user_id==current_user.id, models.Category.type=="income").first()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category")
    income = models.Income(
        user_id=current_user.id,
        category_id=payload.category_id,
        title=payload.title,
        amount=payload.amount,
        description=payload.description,
        date=payload.date
    )
    db.add(income)
    db.commit()
    db.refresh(income)
    return income

@router.get("/", response_model=List[schemas.TransactionResponse])
def list_incomes(month: int | None = Query(None), year: int | None = Query(None), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Income).filter(models.Income.user_id==current_user.id)
    if month and year:
        q = q.filter(models.Income.date.year == year)  # SQLAlchemy doesn't support .year directly; use extract
    from sqlalchemy import extract
    if month:
        q = q.filter(extract('month', models.Income.date) == month)
    if year:
        q = q.filter(extract('year', models.Income.date) == year)
    return q.order_by(models.Income.date.desc()).all()
