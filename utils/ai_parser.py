import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any

try:
    from llama_cpp import Llama
    _LLAMA_AVAILABLE = True
except Exception:
    Llama = None  # type: ignore
    _LLAMA_AVAILABLE = False


def _normalize_amount(raw: str) -> int | None:
    if not raw:
        return None
    s = raw.lower().strip()
    s = s.replace(".", "").replace(",", "")
    # handle common shorthand: 15rb, 15k, 15ribu, 1.5jt
    m = re.match(r"^(\d+(?:[\.,]\d+)?)(\s*)(rb|ribu|k|jt|juta)?$", s)
    if not m:
        # try to extract digits
        nums = re.findall(r"\d+", s)
        if not nums:
            return None
        return int(nums[-1])
    val = float(m.group(1).replace(",", "."))
    unit = m.group(3)
    if not unit:
        return int(val)
    if unit in ("rb", "ribu", "k"):
        return int(val * 1000)
    if unit in ("jt", "juta"):
        return int(val * 1000000)
    return int(val)


def _rule_based_parse(text: str) -> Dict[str, Any]:
    text = text.strip()
    # date detection: keywords like kemarin, hari ini, tanggal YYYY-MM-DD
    today = datetime.utcnow().date()
    date = None
    if re.search(r"\bkemarin\b", text, re.I):
        date = today - timedelta(days=1)
    elif re.search(r"\bhari ini\b|\btoday\b", text, re.I):
        date = today
    else:
        # ISO date
        m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if m:
            try:
                date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except Exception:
                date = None

    # amount detection
    amount = None
    # common patterns: '15rb', '15 ribu', '15.000', '15000', '15k', '1.5jt'
    m_amt = re.search(r"(\d+[\d\.,]*\s*(?:rb|ribu|k|jt|juta)?)(?!\w)", text, re.I)
    if m_amt:
        amount = _normalize_amount(m_amt.group(1))

    # title: pick phrase between verbs like 'beli','membeli' and amount/location
    title = None
    m_title = re.search(r"(?:beli|membeli|makan|minum|bayar)\s+(.*?)(?:\s+\d|\s+di\s+|$)", text, re.I)
    if m_title:
        title = m_title.group(1).strip()
    else:
        # fallback: first 4-6 words
        words = re.findall(r"\w+", text)
        title = " ".join(words[:6]) if words else text

    # Auto-detect type (income vs expense) based on keywords
    trans_type = "expense"  # default to expense
    income_keywords = {
        "gaji", "salary", "pendapatan", "income", "terima", "penerimaan", 
        "penghasilan", "masuk", "transfer masuk", "bonus", "thr", "fee", 
        "honor", "hadiah", "bayaran", "diterima", "dapat", "untung", "profit"
    }
    expense_keywords = {
        "beli", "membeli", "bayar", "belanja", "makan", "buat", "keluar",
        "pengeluaran", "expense", "spend", "kirim", "transfer keluar"
    }
    
    text_lower = text.lower()
    # Check income first (more specific)
    for keyword in income_keywords:
        if re.search(rf"\b{keyword}\b", text_lower):
            trans_type = "income"
            break
    
    # If not income, check expense keywords
    if trans_type == "expense":
        for keyword in expense_keywords:
            if re.search(rf"\b{keyword}\b", text_lower):
                trans_type = "expense"
                break

    # category simple mapping
    category = "other"
    cat_map = {
        "makan": "makan",
        "makanan": "makan",
        "transport": "transport",
        "bensin": "transport",
        "kopi": "minuman",
        "minum": "minuman",
        "ritel": "belanja",
        "gaji": "gaji",
        "salary": "gaji",
        "pendapatan": "pendapatan",
    }
    for k, v in cat_map.items():
        if re.search(rf"\b{k}\b", text, re.I):
            category = v
            break

    return {
        "title": title,
        "amount": amount,
        "date": date.strftime("%Y-%m-%d") if date else datetime.utcnow().date().strftime("%Y-%m-%d"),
        "category": category,
        "type": trans_type,
    }


def parse_expense_text(text: str) -> Dict[str, Any]:
    """Parse Indonesian natural-language expense text into structured dict.

    Returns dict with keys: title, amount (int in IDR), date (YYYY-MM-DD), category.
    On failure returns {'error': 'message'}
    """
    text = (text or "").strip()
    if not text:
        return {"error": "text is empty"}

    # If Llama is available, attempt a deterministic call
    if _LLAMA_AVAILABLE and Llama is not None:
        try:
            llm = Llama(model_path="./models/qwen2-0_5b-instruct-q8_0.gguf", n_threads=4)
            prompt = (
                "Kamu adalah AI yang mengekstrak data transaksi dari teks berbahasa Indonesia."
                "Berikan output persis dalam JSON berikut tanpa penjelasan tambahan:"
                "\n{"
                "\"title\": \"{title}\", \"amount\": {amount}, \"date\": \"{date}\", \"category\": \"{category}\", \"type\": \"{type}\"}"
                "\nType bisa 'income' (pendapatan/terima uang) atau 'expense' (pengeluaran/beli/bayar)."
            )
            # naive defaults
            defaults = {"title": "", "amount": 0, "date": datetime.utcnow().date().strftime("%Y-%m-%d"), "category": "other", "type": "expense"}
            task = f"Teks: \"{text}\"\n\nContoh format JSON: {json.dumps(defaults)}\n\nKeluarkan JSON saja."
            full_prompt = prompt + "\n" + task
            resp = llm(full_prompt, max_tokens=200, temperature=0)
            out = ""
            # llama_cpp returns different shapes across versions
            try:
                out = resp["choices"][0]["text"]
            except Exception:
                out = resp.get("text", "")

            out = out.strip()
            # try to extract JSON object
            jmatch = re.search(r"\{.*\}", out, re.S)
            if jmatch:
                jstr = jmatch.group(0)
                try:
                    parsed = json.loads(jstr)
                    # normalize amount
                    if "amount" in parsed:
                        parsed_amount = _normalize_amount(str(parsed.get("amount")))
                        parsed["amount"] = parsed_amount if parsed_amount is not None else parsed.get("amount")
                    return parsed
                except Exception:
                    # fall through to fallback
                    pass
        except Exception:
            # Llama call failed; continue to fallback
            pass

    # fallback rule-based parsing
    try:
        return _rule_based_parse(text)
    except Exception as e:
        return {"error": f"parse failed: {str(e)}"}

