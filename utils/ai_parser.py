# utils/ai_parser.py
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from .rule_parser import _extract_date_from_text, _extract_category_from_text, _extract_amount_from_text, _has_transaction_content

try:
    from llama_cpp import Llama
    _LLAMA_AVAILABLE = True
except Exception:
    Llama = None  # type: ignore
    _LLAMA_AVAILABLE = False





def parse_expense_text(text: str) -> Dict[str, Any]:
    """Parse Indonesian natural-language expense text into structured dict using AI model.

    Returns dict with keys: title, amount (int in IDR), date (YYYY-MM-DD), category, type.
    On failure returns {'error': 'message'}
    """
    text = (text or "").strip()
    if not text:
        return {"error": "text is empty"}

    # ✅ VALIDASI AWAL: Check if text contains actual transaction content
    if not _has_transaction_content(text):
        return {"error": "Teks tidak mengandung informasi transaksi. Silakan sebutkan apa yang dibeli/dibayar dan nominalnya. Contoh: 'beli kopi 15rb kemarin'"}

    # Check if AI model is available
    if not _LLAMA_AVAILABLE or Llama is None:
        return {"error": "AI model (llama-cpp-python) tidak tersedia. Install dengan: pip install llama-cpp-python"}

    try:
        # ✅ PRE-PROCESS: Extract date, category, and amount using regex (faster & more reliable)
        detected_date = _extract_date_from_text(text)
        detected_category = _extract_category_from_text(text)
        detected_amount = _extract_amount_from_text(text)
        
        print(f"🔍 Pre-processing:")
        print(f"   - Detected date: {detected_date}")
        print(f"   - Detected category: {detected_category}")
        print(f"   - Detected amount: {detected_amount}")
        
        # ✅ VALIDASI: Amount harus ada
        if detected_amount is None:
            return {"error": "Nominal/harga tidak disebutkan dalam teks. Silakan tambahkan jumlah uang. Contoh: '15rb', 'Rp15.000', '15ribu', '10 juta'"}

        # Initialize AI model
        llm = Llama(model_path="./models/DeepSeek-R1-Distill-Qwen-1.5B-Q8_0.gguf", 
                    n_threads=4, 
                    n_ctx=2048,
                    verbose=False)
        
        # Enhanced prompt with MORE DETAILED examples
        today = datetime.utcnow().date().strftime("%Y-%m-%d")
        yesterday = (datetime.utcnow().date() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        prompt = f"""TUGAS:
        Klasifikasikan transaksi keuangan dari teks Bahasa Indonesia.

        KELUARKAN HANYA JSON VALID.
        JANGAN tambahkan penjelasan, thinking process, atau teks apapun selain JSON.
        JANGAN ubah format.

        FORMAT WAJIB:
        {{"title":"...", "amount":number, "date":"YYYY-MM-DD", "category":"...", "type":"expense|income"}}

        ATURAN AMOUNT (PENTING):
        - WAJIB ambil amount dari teks
        - 15rb/15ribu/15k → amount=15000
        - 1.5jt/1.5juta → amount=1500000
        - 10 juta → amount=10000000
        - Rp15.000 → amount=15000

        ATURAN TYPE (WAJIB):
        - Kata: beli, membeli, bayar, belanja, makan, minum, bensin, kopi → type="expense"
        - Kata: gaji, terima, pendapatan, bonus, hasil, dapat, mendapatkan → type="income"
        - Default: type="expense"

        ATURAN KATEGORI (PRIORITAS TINGGI):
        - kopi/teh/jus/minuman → category="minuman"
        - nasi/ayam/makan/sarapan → category="makan"
        - bensin/ojek/gojek/grab/taxi/bus → category="transport"
        - gaji/salary/penghasilan/pendapatan → category="gaji"
        - listrik/air/wifi/pulsa → category="tagihan"
        - Jika TIDAK COCOK → category="other"

        ATURAN TANGGAL:
        - "hari ini" atau "today" → date="{today}"
        - "kemarin" atau "yesterday" → date="{yesterday}"
        - "2 hari lalu" → date="{(datetime.utcnow().date() - timedelta(days=2)).strftime('%Y-%m-%d')}"
        - Jika TIDAK DISEBUT → date="{today}"

        CONTOH BENAR:

        Input: beli kopi 15rb kemarin
        Output:
        {{"title":"Beli kopi","amount":15000,"date":"{yesterday}","category":"minuman","type":"expense"}}

        Input: saya membeli kopi hari ini seharga Rp15.000
        Output:
        {{"title":"Membeli kopi","amount":15000,"date":"{today}","category":"minuman","type":"expense"}}

        Input: bayar bensin 50rb
        Output:
        {{"title":"Bayar bensin","amount":50000,"date":"{today}","category":"transport","type":"expense"}}

        Input: terima gaji 5jt hari ini
        Output:
        {{"title":"Terima gaji","amount":5000000,"date":"{today}","category":"gaji","type":"income"}}

        Input: mendapatkan gaji 10 juta
        Output:
        {{"title":"Mendapatkan gaji","amount":10000000,"date":"{today}","category":"gaji","type":"income"}}

        SEKARANG PROSES TEKS INI:
        {text}

        OUTPUT JSON (tanpa penjelasan):
        """

        # Get AI response
        print(f"🤖 Processing with AI...")
        resp = llm(prompt, max_tokens=256, temperature=0.1, stop=["\n\n", "Input:", "SEKARANG", "OUTPUT"])
        
        # Extract response text
        out = ""
        try:
            out = resp["choices"][0]["text"]
        except Exception:
            out = resp.get("text", "")

        out = out.strip()
        print(f"📤 AI raw output: {out[:200]}")
        
        # Extract JSON from response (handle multiple formats)
        jmatch = re.search(r'\{[^}]+\}', out, re.S)
        if not jmatch:
            return {"error": f"AI tidak menghasilkan JSON valid. Response: {out[:100]}"}
        
        jstr = jmatch.group(0)
        parsed = json.loads(jstr)
        
        # ✅ POST-PROCESS: Override with detected values (regex lebih akurat)
        if detected_date:
            print(f"✅ Overriding date: {parsed.get('date')} → {detected_date}")
            parsed["date"] = detected_date
        
        if detected_category:
            print(f"✅ Overriding category: {parsed.get('category')} → {detected_category}")
            parsed["category"] = detected_category
        
        if detected_amount is not None:
            print(f"✅ Overriding amount: {parsed.get('amount')} → {detected_amount}")
            parsed["amount"] = detected_amount
        
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
        
        # ✅ FINAL VALIDATION: Amount must exist
        if not parsed.get("amount") or parsed.get("amount") == 0:
            return {"error": "Nominal/harga tidak dapat dideteksi. Pastikan format benar. Contoh: '15rb', 'Rp15.000', '15000', '10 juta'"}
        
        print(f"✅ Final parsed result: {parsed}")
        return parsed
        
    except json.JSONDecodeError as e:
        return {"error": f"AI menghasilkan JSON tidak valid: {str(e)}"}
    except Exception as e:
        return {"error": f"AI parsing gagal: {str(e)}"}