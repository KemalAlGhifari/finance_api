from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from utils.ai_parser import parse_expense_text
from auth import get_current_user, get_db
from datetime import datetime
import models

router = APIRouter(prefix="/ai")



@router.post("/parse-expense")
def parse_expense(
    text: str,
    override_title: str | None = None,
    override_amount: float | None = None,
    override_date: str | None = None,
    override_category: str | None = None,
    override_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Parse text and automatically save to income or expense table based on detected type.

    Use `override_type` to force 'income' or 'expense'."""
    data = parse_expense_text(text)
    if "error" in data:
        return {"success": False, "detail": data["error"]}

    # apply overrides
    if override_title:
        data["title"] = override_title
    if override_amount is not None:
        try:
            data["amount"] = int(override_amount)
        except Exception:
            pass
    if override_date:
        try:
            datetime.strptime(override_date, "%Y-%m-%d")
            data["date"] = override_date
        except Exception:
            pass
    if override_category:
        data["category"] = override_category

    # determine record type
    record_type = "expense"
    if data.get("type") in ("income", "expense"):
        record_type = data.get("type")
    if override_type in ("income", "expense"):
        record_type = override_type
    income_keywords = {"income", "incom", "gaji", "penerimaan", "salary", "pendapatan", "terima"}
    if data.get("category") and str(data.get("category")).lower() in income_keywords:
        record_type = "income"

    # find a default category for this user and type
    try:
        cat_type = models.CategoryType.income if record_type == "income" else models.CategoryType.expense
        category = db.query(models.Category).filter(models.Category.user_id == current_user.id, models.Category.type == cat_type).first()
    except Exception:
        category = None

    try:
        if record_type == "income":
            income = models.Income(
                user_id=current_user.id,
                category_id=category.id if category else None,
                title=data["title"],
                amount=data["amount"],
                date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
                description=""
            )
            db.add(income)
            db.commit()
            db.refresh(income)

            return {"success": True, "saved": True, "data": {
                "id": income.id,
                "title": income.title,
                "amount": income.amount,
                "date": str(income.date),
                "category": category.name if category else None,
                "type": "income"
            }}
        else:
            expense = models.Expense(
                user_id=current_user.id,
                category_id=category.id if category else None,
                title=data["title"],
                amount=data["amount"],
                date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
                description=""
            )
            db.add(expense)
            db.commit()
            db.refresh(expense)

            return {"success": True, "saved": True, "data": {
                "id": expense.id,
                "title": expense.title,
                "amount": expense.amount,
                "date": str(expense.date),
                "category": category.name if category else None,
                "type": "expense"
            }}
    except Exception as e:
        db.rollback()
        return {"success": False, "detail": f"Gagal menyimpan record: {str(e)}"}


@router.post("/parse-expense/preview")
def parse_expense_preview(
    text: str,
    override_title: str | None = None,
    override_amount: float | None = None,
    override_date: str | None = None,
    override_category: str | None = None,
):
    """Preview parsing result without saving. Accepts overrides as query params or body fields."""
    data = parse_expense_text(text)
    if "error" in data:
        return {"success": False, "detail": data["error"]}

    # apply overrides
    if override_title:
        data["title"] = override_title
    if override_amount is not None:
        try:
            data["amount"] = int(override_amount)
        except Exception:
            pass
    if override_date:
        try:
            datetime.strptime(override_date, "%Y-%m-%d")
            data["date"] = override_date
        except Exception:
            pass
    if override_category:
        data["category"] = override_category

    return {"success": True, "parsed": data}
