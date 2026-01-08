# expense_parser.py
from .ai_parser import ai_extract
from .rule_parser import rule_guard

def parse_expense_text(text: str):
    if not text.strip():
        return {"error": "text kosong"}

    ai_data = ai_extract(text)
    result = rule_guard(text, ai_data)

    for k in ["title", "amount", "date", "category", "type"]:
        if result.get(k) is None:
            return {"error": f"gagal parse {k}"}

    return result
