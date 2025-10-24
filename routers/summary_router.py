# routers/summary_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from auth import get_db, get_current_user
import models
from typing import List
from datetime import datetime
import schemas

router = APIRouter(prefix="/summary", tags=["summary"])

@router.get("/daily", response_model=schemas.SummaryResponse)
def summary_daily(date: str = Query(..., description="YYYY-MM-DD"), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # parse date
    dt = datetime.strptime(date, "%Y-%m-%d").date()
    income_total = db.query(func.IFNULL(func.sum(models.Income.amount), 0)).filter(models.Income.user_id==current_user.id, models.Income.date==dt).scalar() or 0
    expense_total = db.query(func.IFNULL(func.sum(models.Expense.amount), 0)).filter(models.Expense.user_id==current_user.id, models.Expense.date==dt).scalar() or 0
    return {"income": float(income_total), "expense": float(expense_total), "balance": float(income_total) - float(expense_total)}

@router.get("/monthly")
def summary_monthly(month: int = Query(...), year: int = Query(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # total income & expense
    income_total = db.query(func.IFNULL(func.sum(models.Income.amount),0)).filter(models.Income.user_id==current_user.id, extract('month', models.Income.date)==month, extract('year', models.Income.date)==year).scalar() or 0
    expense_total = db.query(func.IFNULL(func.sum(models.Expense.amount),0)).filter(models.Expense.user_id==current_user.id, extract('month', models.Expense.date)==month, extract('year', models.Expense.date)==year).scalar() or 0

    # breakdown by category
    income_by_cat = db.query(models.Category.name, func.sum(models.Income.amount).label('total'))\
        .join(models.Income, models.Income.category_id==models.Category.id)\
        .filter(models.Category.user_id==current_user.id, models.Category.type=='income', extract('month', models.Income.date)==month, extract('year', models.Income.date)==year)\
        .group_by(models.Category.id).all()

    expense_by_cat = db.query(models.Category.name, func.sum(models.Expense.amount).label('total'))\
        .join(models.Expense, models.Expense.category_id==models.Category.id)\
        .filter(models.Category.user_id==current_user.id, models.Category.type=='expense', extract('month', models.Expense.date)==month, extract('year', models.Expense.date)==year)\
        .group_by(models.Category.id).all()

    by_category = []
    for name, total in income_by_cat:
        by_category.append({"category": name, "income": float(total)})
    for name, total in expense_by_cat:
        by_category.append({"category": name, "expense": float(total)})

    return {
        "total_income": float(income_total),
        "total_expense": float(expense_total),
        "balance": float(income_total) - float(expense_total),
        "by_category": by_category
    }

@router.get("/yearly")
def summary_yearly(year: int = Query(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # returns monthly breakdown for the year
    results = []
    for m in range(1,13):
        income_total = db.query(func.IFNULL(func.sum(models.Income.amount),0)).filter(models.Income.user_id==current_user.id, extract('month', models.Income.date)==m, extract('year', models.Income.date)==year).scalar() or 0
        expense_total = db.query(func.IFNULL(func.sum(models.Expense.amount),0)).filter(models.Expense.user_id==current_user.id, extract('month', models.Expense.date)==m, extract('year', models.Expense.date)==year).scalar() or 0
        results.append({
            "month": m,
            "income": float(income_total),
            "expense": float(expense_total),
            "balance": float(income_total) - float(expense_total)
        })
    return results
