# routers/transactions_router.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from typing import List, Literal
from datetime import datetime, timedelta
import models
from auth import get_db, get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("")
def get_transactions(
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all transactions for a specific month or date range"""
    try:
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            start = datetime(year, month, 1).date()
            # Get last day of month
            if month == 12:
                end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end = datetime(year, month + 1, 1).date() - timedelta(days=1)
    except ValueError:
        return {"success": False, "detail": "Invalid date format"}
    
    # Get incomes
    incomes = db.query(models.Income).filter(
        models.Income.user_id == current_user.id,
        models.Income.date >= start,
        models.Income.date <= end
    ).order_by(models.Income.date.desc()).all()
    
    # Get expenses
    expenses = db.query(models.Expense).filter(
        models.Expense.user_id == current_user.id,
        models.Expense.date >= start,
        models.Expense.date <= end
    ).order_by(models.Expense.date.desc()).all()
    
    # Combine and format transactions
    transactions = []
    
    for income in incomes:
        transactions.append({
            "id": income.id,
            "category_id": income.category_id,
            "title": income.title,
            "amount": income.amount,
            "description": income.description or "",
            "date": str(income.date),
            "type": "income",
            "category": {
                "id": income.category.id,
                "name": income.category.name
            } if income.category else None
        })
    
    for expense in expenses:
        transactions.append({
            "id": expense.id,
            "category_id": expense.category_id,
            "title": expense.title,
            "amount": expense.amount,
            "description": expense.description or "",
            "date": str(expense.date),
            "type": "expense",
            "category": {
                "id": expense.category.id,
                "name": expense.category.name
            } if expense.category else None
        })
    
    # Sort by date descending
    transactions.sort(key=lambda x: x["date"], reverse=True)
    
    # Calculate summary
    total_income = sum(inc.amount for inc in incomes)
    total_expense = sum(exp.amount for exp in expenses)
    
    return {
        "data": transactions,
        "summary": {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense
        }
    }


@router.get("/summary/monthly")
def get_monthly_summary(
    year: int = Query(..., description="Year"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get monthly summary for entire year"""
    month_names = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                   "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    
    # Get all transactions for the year
    incomes = db.query(models.Income).filter(
        models.Income.user_id == current_user.id,
        extract('year', models.Income.date) == year
    ).all()
    
    expenses = db.query(models.Expense).filter(
        models.Expense.user_id == current_user.id,
        extract('year', models.Expense.date) == year
    ).all()
    
    # Group by month
    monthly_data = {}
    for month_num in range(1, 13):
        monthly_data[month_num] = {
            "month": month_num,
            "month_name": month_names[month_num - 1],
            "total_income": 0,
            "total_expense": 0,
            "balance": 0,
            "transaction_count": 0
        }
    
    # Sum incomes by month
    for income in incomes:
        month_num = income.date.month
        monthly_data[month_num]["total_income"] += income.amount
        monthly_data[month_num]["transaction_count"] += 1
    
    # Sum expenses by month
    for expense in expenses:
        month_num = expense.date.month
        monthly_data[month_num]["total_expense"] += expense.amount
        monthly_data[month_num]["transaction_count"] += 1
    
    # Calculate balance
    for month_num in monthly_data:
        monthly_data[month_num]["balance"] = monthly_data[month_num]["total_income"] - monthly_data[month_num]["total_expense"]
    
    # Convert to list and filter out empty months (optional: keep all months)
    result_data = [monthly_data[i] for i in range(1, 13)]
    
    return {
        "year": year,
        "data": result_data
    }


@router.get("/summary/weekly")
def get_weekly_summary(
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get weekly summary for a specific month"""
    # Get first and last day of month
    first_day = datetime(year, month, 1).date()
    if month == 12:
        last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # Get all transactions for the month
    incomes = db.query(models.Income).filter(
        models.Income.user_id == current_user.id,
        models.Income.date >= first_day,
        models.Income.date <= last_day
    ).all()
    
    expenses = db.query(models.Expense).filter(
        models.Expense.user_id == current_user.id,
        models.Expense.date >= first_day,
        models.Expense.date <= last_day
    ).all()
    
    # Calculate weeks
    weekly_data = []
    current_date = first_day
    week_num = 1
    
    while current_date <= last_day:
        # Find start of week (Monday)
        week_start = current_date - timedelta(days=current_date.weekday())
        # Find end of week (Sunday)
        week_end = week_start + timedelta(days=6)
        
        # Adjust if week extends beyond month
        if week_start < first_day:
            week_start = first_day
        if week_end > last_day:
            week_end = last_day
        
        # Filter transactions for this week
        week_incomes = [inc for inc in incomes if week_start <= inc.date <= week_end]
        week_expenses = [exp for exp in expenses if week_start <= exp.date <= week_end]
        
        total_income = sum(inc.amount for inc in week_incomes)
        total_expense = sum(exp.amount for exp in week_expenses)
        
        weekly_data.append({
            "week_number": week_num,
            "start_date": str(week_start),
            "end_date": str(week_end),
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
            "transaction_count": len(week_incomes) + len(week_expenses)
        })
        
        week_num += 1
        current_date = week_end + timedelta(days=1)
    
    return {
        "year": year,
        "month": month,
        "data": weekly_data
    }

