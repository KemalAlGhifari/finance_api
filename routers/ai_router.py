from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from utils.ai_parser import parse_expense_text
from auth import get_current_user, get_db
from datetime import datetime
import models

router = APIRouter(prefix="/ai")



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
