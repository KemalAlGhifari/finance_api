# routers/expenses_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from auth import get_db, get_current_user
from sqlalchemy import extract

router = APIRouter(prefix="/expenses", tags=["expenses"])

@router.post("/", response_model=schemas.TransactionResponse)
def create_expense(payload: schemas.ExpenseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if payload.category_id:
        cat = db.query(models.Category).filter(models.Category.id==payload.category_id, models.Category.user_id==current_user.id, models.Category.type=="expense").first()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category")
    expense = models.Expense(
        user_id=current_user.id,
        category_id=payload.category_id,
        title=payload.title,
        amount=payload.amount,
        description=payload.description,
        date=payload.date
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense

@router.get("/", response_model=List[schemas.TransactionResponse])
def list_expenses(month: int | None = Query(None), year: int | None = Query(None), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Expense).filter(models.Expense.user_id==current_user.id)
    if month:
        q = q.filter(extract('month', models.Expense.date) == month)
    if year:
        q = q.filter(extract('year', models.Expense.date) == year)
    return q.order_by(models.Expense.date.desc()).all()
