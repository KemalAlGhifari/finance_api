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


def parse_expense_text(text: str) -> Dict[str, Any]:
    """Parse Indonesian natural-language expense text into structured dict using AI model.

    Returns dict with keys: title, amount (int in IDR), date (YYYY-MM-DD), category, type.
    On failure returns {'error': 'message'}
    """
    text = (text or "").strip()
    if not text:
        return {"error": "text is empty"}

    # Check if AI model is available
    if not _LLAMA_AVAILABLE or Llama is None:
        return {"error": "AI model (llama-cpp-python) tidak tersedia. Install dengan: pip install llama-cpp-python"}

    try:
        # Initialize AI model
        llm = Llama(model_path="./models/DeepSeek-R1-Distill-Qwen-1.5B-Q8_0.gguf", n_threads=4, n_ctx=2048)
        
        # Enhanced prompt with detailed instructions and examples
        today = datetime.utcnow().date().strftime("%Y-%m-%d")
        prompt = f"""
            TUGAS:
            Klasifikasikan transaksi keuangan dari teks Bahasa Indonesia.

            KELUARKAN HANYA JSON VALID.
            JANGAN tambahkan penjelasan.
            JANGAN ubah format.

            FORMAT WAJIB:
            {{"title":"...", "amount":number, "date":"YYYY-MM-DD", "category":"...", "type":"expense|income"}}

            ATURAN KERAS (WAJIB DIPATUHI):
            - Jika teks mengandung kata: beli, membeli, bayar, belanja, makan, minum, bensin, kopi
            MAKA type = "expense" (TIDAK BOLEH income)
            - Jika teks mengandung kata: gaji, terima, pendapatan, bonus, hasil
            MAKA type = "income" (TIDAK BOLEH expense)
            - Jika TIDAK JELAS, default type = "expense"

            KATEGORI:
            - makan → makan
            - minum/kopi → minuman
            - bensin/ojek/bus → transport
            - gaji → gaji
            - lainnya → other

            NOMINAL:
            - 15rb=15000
            - 1.5jt=1500000

            TANGGAL:
            - hari ini = {today}
            - kemarin = {(datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")}
            - jika tidak disebut → {today}

            CONTOH BENAR:
            Input: saya membeli makan 18rb
            Output:
            {{"title":"Membeli makan","amount":18000,"date":"{today}","category":"makan","type":"expense"}}

            Input: terima gaji 5jt
            Output:
            {{"title":"Terima gaji","amount":5000000,"date":"{today}","category":"gaji","type":"income"}}

            TEKS:
            {text}

            JSON:
            """


        # Get AI response
        resp = llm(prompt, max_tokens=256, temperature=0.1, stop=["\n\n", "Input:", "Teks:"])
        
        # Extract response text
        out = ""
        try:
            out = resp["choices"][0]["text"]
        except Exception:
            out = resp.get("text", "")

        out = out.strip()
        
        # Extract JSON from response
        jmatch = re.search(r"\{.*?\}", out, re.S)
        if not jmatch:
            return {"error": f"AI tidak menghasilkan JSON valid. Response: {out[:100]}"}
        
        jstr = jmatch.group(0)
        parsed = json.loads(jstr)
        
       
        
        # Ensure all required fields exist with defaults
        parsed.setdefault("title", text[:50])
        parsed.setdefault("date", today)
        parsed.setdefault("category", "other")
        parsed.setdefault("type", "expense")
        
        # Validate date format
        try:
            datetime.strptime(parsed["date"], "%Y-%m-%d")
        except Exception:
            parsed["date"] = today
        
        return parsed
        
    except json.JSONDecodeError as e:
        return {"error": f"AI menghasilkan JSON tidak valid: {str(e)}"}
    except Exception as e:
        return {"error": f"AI parsing gagal: {str(e)}"}

