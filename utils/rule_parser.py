import re
import json
from datetime import datetime, timedelta
from typing import Dict, Any

def _normalize_amount(raw: str) -> int | None:
    """Extract amount from Indonesian text."""
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


def _extract_date_from_text(text: str) -> str | None:
    """Extract date from Indonesian text using regex."""
    text_lower = text.lower()
    today = datetime.utcnow().date()
    
    # Check for "hari ini" or "today"
    if re.search(r'\b(hari ini|today)\b', text_lower):
        return today.strftime("%Y-%m-%d")
    
    # Check for "kemarin" or "yesterday"
    if re.search(r'\b(kemarin|yesterday)\b', text_lower):
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # ✅ FIX 1: Handle "tiga hari yang lalu" (kata → angka)
    number_words = {
        'satu': 1, 'dua': 2, 'tiga': 3, 'empat': 4, 'lima': 5,
        'enam': 6, 'tujuh': 7, 'delapan': 8, 'sembilan': 9, 'sepuluh': 10,
        'sebelas': 11, 'dua belas': 12, 'tiga belas': 13, 'empat belas': 14, 'lima belas': 15
    }
    
    # Check for "tiga hari yang lalu" or "tiga hari lalu"
    for word, num in number_words.items():
        pattern = rf'\b{word}\s+hari\s*(yang)?\s*lalu\b'
        if re.search(pattern, text_lower):
            return (today - timedelta(days=num)).strftime("%Y-%m-%d")
    
    # Check for "2 hari yang lalu" or "2 hari lalu" (angka)
    match = re.search(r'(\d+)\s*hari\s*(yang)?\s*lalu', text_lower)
    if match:
        days_ago = int(match.group(1))
        return (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    
    # ✅ FIX 2: Handle "tanggal DD bulan MM YYYY" or "DD bulan MM YYYY"
    months = {
        'januari': 1, 'jan': 1,
        'februari': 2, 'feb': 2,
        'maret': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'mei': 5,
        'juni': 6, 'jun': 6,
        'juli': 7, 'jul': 7,
        'agustus': 8, 'agu': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'oktober': 10, 'okt': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'desember': 12, 'des': 12, 'dec': 12,
    }
    
    # Match "tanggal 1 bulan 1 2025" or "1 bulan 1 2025"
    match = re.search(r'(?:tanggal\s+)?(\d{1,2})\s+bulan\s+(\d{1,2})\s+(\d{4})', text_lower)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        try:
            date_obj = datetime(year, month, day).date()
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # ✅ NEW: Match "di bulan Februari tanggal 1" or "bulan februari tanggal 1"
    for month_name, month_num in months.items():
        # Pattern: "di bulan MONTH tanggal DD"
        pattern = rf'(?:di\s+)?bulan\s+{month_name}\s+tanggal\s+(\d{{1,2}})'
        match = re.search(pattern, text_lower)
        if match:
            day = int(match.group(1))
            # Try with current year first
            try:
                date_obj = datetime(today.year, month_num, day).date()
                # If date is in the past, use next year
                if date_obj < today:
                    date_obj = datetime(today.year + 1, month_num, day).date()
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass
        
        # Pattern: "tanggal DD bulan MONTH" or "tanggal DD di bulan MONTH"
        pattern = rf'tanggal\s+(\d{{1,2}})\s+(?:di\s+)?bulan\s+{month_name}'
        match = re.search(pattern, text_lower)
        if match:
            day = int(match.group(1))
            try:
                date_obj = datetime(today.year, month_num, day).date()
                if date_obj < today:
                    date_obj = datetime(today.year + 1, month_num, day).date()
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass
    
    # Match "5 januari 2025" or "5 jan 2025"
    for month_name, month_num in months.items():
        pattern = rf'(\d{{1,2}})\s+{month_name}\s+(\d{{4}})\b'
        match = re.search(pattern, text_lower)
        if match:
            day = int(match.group(1))
            year = int(match.group(2))
            try:
                date_obj = datetime(year, month_num, day).date()
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass
    
    # Check for specific date formats: "5 januari", "5 jan", etc (tanpa tahun, pakai tahun sekarang)
    for month_name, month_num in months.items():
        pattern = rf'(\d{{1,2}})\s+{month_name}\b'
        match = re.search(pattern, text_lower)
        if match:
            day = int(match.group(1))
            try:
                date_obj = datetime(today.year, month_num, day).date()
                # If date is in the past, use next year
                if date_obj < today:
                    date_obj = datetime(today.year + 1, month_num, day).date()
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                pass
    
    # ✅ FIX 3: Handle ISO format "YYYY-MM-DD" or "DD-MM-YYYY" or "DD/MM/YYYY"
    # ISO format: 2025-01-01
    match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text_lower)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            date_obj = datetime(year, month, day).date()
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # DD-MM-YYYY or DD/MM/YYYY
    match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', text_lower)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        try:
            date_obj = datetime(year, month, day).date()
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    return None


def _extract_category_from_text(text: str) -> str | None:
    """Extract category from Indonesian text using keyword matching."""
    text_lower = text.lower()
    
    # Category keywords mapping (most specific first)
    category_keywords = {
        'makan': ['nasi', 'ayam', 'soto', 'bakso', 'mie', 'bubur', 'sate', 
                  'rendang', 'gudeg', 'pecel', 'gado', 'warteg', 'padang',
                  'resto', 'restoran', 'makanan', 'makan', 'sarapan', 
                  'makan siang', 'makan malam'],
        'minuman': ['kopi', 'teh', 'jus', 'susu', 'air mineral', 'aqua',
                    'minuman', 'minum', 'es', 'cappuccino', 'latte', 'espresso',
                    'americano', 'boba', 'milkshake', 'smoothie'],
        'transport': ['bensin', 'ojek', 'gojek', 'grab', 'taxi', 'taksi',
                      'bus', 'kereta', 'transportasi', 'parkir', 'tol',
                      'angkot', 'angkutan', 'bbm', 'pertamax'],
        'belanja': ['beli', 'belanja', 'shopping', 'supermarket', 'indomaret',
                    'alfamart', 'pasar', 'toko'],
        'tagihan': ['listrik', 'air', 'pdam', 'wifi', 'internet', 'pulsa',
                    'token', 'tagihan', 'bayar cicilan', 'cicilan'],
        'hiburan': ['nonton', 'bioskop', 'cinema', 'karaoke', 'game', 'netflix',
                    'spotify', 'youtube premium', 'hiburan'],
        'kesehatan': ['obat', 'dokter', 'rumah sakit', 'rs', 'klinik', 'apotek',
                      'vitamin', 'kesehatan'],
        'gaji': ['gaji', 'salary', 'penghasilan', 'pendapatan', 'income'],
    }
    
    # Check each category
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category
    
    return None


def _extract_amount_from_text(text: str) -> int | None:
    """Extract amount from Indonesian text."""
    text_lower = text.lower()
    
    # ✅ NEW: Pattern for "10 juta" or "sepuluh juta" (kata + juta/ribu)
    number_words_full = {
        'satu': 1, 'dua': 2, 'tiga': 3, 'empat': 4, 'lima': 5,
        'enam': 6, 'tujuh': 7, 'delapan': 8, 'sembilan': 9, 'sepuluh': 10,
        'sebelas': 11, 'dua belas': 12, 'tiga belas': 13, 'empat belas': 14, 'lima belas': 15,
        'dua puluh': 20, 'tiga puluh': 30, 'empat puluh': 40, 'lima puluh': 50,
        'enam puluh': 60, 'tujuh puluh': 70, 'delapan puluh': 80, 'sembilan puluh': 90,
        'seratus': 100, 'seribu': 1000
    }
    
    # Check for "sepuluh juta", "lima ribu", etc
    for word, num in number_words_full.items():
        # Match "sepuluh juta"
        pattern = rf'\b{word}\s+juta\b'
        if re.search(pattern, text_lower):
            return num * 1000000
        
        # Match "lima ribu"
        pattern = rf'\b{word}\s+ribu\b'
        if re.search(pattern, text_lower):
            return num * 1000
    
    # Pattern 1: "Rp15.000" or "Rp 15.000" or "rp15000"
    match = re.search(r'rp\.?\s*(\d+(?:[.,]\d+)*)', text_lower)
    if match:
        amount_str = match.group(1).replace('.', '').replace(',', '')
        try:
            return int(amount_str)
        except ValueError:
            pass
    
    # Pattern 2: "15rb" or "15ribu" or "15k"
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(rb|ribu|k)\b', text_lower)
    if match:
        val = float(match.group(1).replace(',', '.'))
        return int(val * 1000)
    
    # Pattern 3: "1.5jt" or "1.5juta" or "10 juta"
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(jt|juta)\b', text_lower)
    if match:
        val = float(match.group(1).replace(',', '.'))
        return int(val * 1000000)
    
    # Pattern 4: "senilai XXX" or "sebesar XXX"
    match = re.search(r'(?:senilai|sebesar|nominal)\s+(\d+(?:[.,]\d+)?)\s*(jt|juta|rb|ribu|k)?\b', text_lower)
    if match:
        val = float(match.group(1).replace(',', '.'))
        unit = match.group(2)
        if unit in ('jt', 'juta'):
            return int(val * 1000000)
        elif unit in ('rb', 'ribu', 'k'):
            return int(val * 1000)
        else:
            # No unit, check if value suggests thousands or millions
            if val >= 1000000:
                return int(val)
            elif val >= 1000:
                return int(val)
            else:
                # Assume it's in thousands if < 1000
                return int(val * 1000) if val < 100 else int(val)
    
    # Pattern 5: Just numbers with thousand separators "15.000"
    match = re.search(r'\b(\d{1,3}(?:\.\d{3})+)\b', text)
    if match:
        amount_str = match.group(1).replace('.', '')
        try:
            return int(amount_str)
        except ValueError:
            pass
    
    # Pattern 6: Just a plain number (as last resort)
    match = re.search(r'\b(\d{3,})\b', text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    
    return None


def _has_transaction_content(text: str) -> bool:
    """Check if text contains actual transaction information (not just date/time words)."""
    text_lower = text.lower().strip()
    
    # Remove common date/time words
    date_words = [
        'hari ini', 'kemarin', 'today', 'yesterday',
        'hari', 'lalu', 'yang', 'tanggal', 'bulan', 'di',
        'januari', 'februari', 'maret', 'april', 'mei', 'juni',
        'juli', 'agustus', 'september', 'oktober', 'november', 'desember',
        'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
        'agu', 'okt', 'des', 'satu', 'dua', 'tiga', 'empat', 'lima',
        'enam', 'tujuh', 'delapan', 'sembilan', 'sepuluh'
    ]
    
    # Remove date patterns and numbers
    cleaned = text_lower
    for word in date_words:
        cleaned = cleaned.replace(word, ' ')
    
    # Remove numbers and common separators
    cleaned = re.sub(r'\d+', '', cleaned)
    cleaned = re.sub(r'[-/,.]', ' ', cleaned)
    cleaned = ' '.join(cleaned.split())  # normalize whitespace
    
    # If after removing date words, there's still meaningful content
    if len(cleaned) < 3:
        return False
    
    # Check if there's at least one action word or item
    action_words = [
        'beli', 'bayar', 'belanja', 'makan', 'minum', 'dapat', 'terima', 'mendapatkan',
        'kopi', 'nasi', 'bensin', 'pulsa', 'token', 'listrik', 'air',
        'gaji', 'bonus', 'ojek', 'grab', 'gojek', 'taxi', 'bus', 'senilai', 'sebesar'
    ]
    
    for word in action_words:
        if word in text_lower:
            return True
    
    return False