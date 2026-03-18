import re

def _first_or_none(matches):
    if not matches: return None
    res = matches[0]
    return res[0] if isinstance(res, tuple) else res

def _clean_amount(val):
    if not val: return 0.0
    # Specifically avoid rates (e.g. 20%)
    if "%" in val: return 0.0
    val = val.replace("€", "").replace("EUR", "").replace(" ", "").replace(",", ".").replace("\xa0", "").strip()
    try:
        # Remove any non-numeric chars except .
        val = re.sub(r"[^0-9\.]", "", val)
        return float(val)
    except:
        return 0.0

def extract_information(text: str) -> dict:
    # 1. Clean OCR artifacts typically seen on photos
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)

    # 2. Key-Value Extraction (very robust for "KEY: VALUE")
    def get_val(key, text):
        m = re.search(rf"{key}\s*[:\-]*\s*([^\n\r]+)", text, flags=re.IGNORECASE)
        return m.group(1).strip() if m else None

    # SIRET/SIREN
    # Try Label first, then global search
    siret = get_val("SIRET", cleaned_text)
    if siret:
        siret = re.sub(r"\D", "", siret)
    else:
        # Global search for 14 digits
        matches = re.findall(r"\b\d{14}\b", cleaned_text)
        siret = matches[0] if matches else None

    # Date
    date_val = get_val("DATE", cleaned_text)
    if not date_val:
        # Global search
        matches = re.findall(r"\b\d{1,2}[/\-\s]\d{1,2}[/\-\s]\d{4}\b", cleaned_text)
        date_val = matches[0] if matches else None

    # Company Name
    company = get_val("COMPANY", cleaned_text)

    # Financials (Very strict labels to avoid confusion)
    total_ht_str = get_val("TOTAL HT", cleaned_text)
    tva_amount_str = get_val("TVA", cleaned_text)
    total_ttc_str = get_val("TOTAL TTC", cleaned_text)

    # 3. Global Fallback for amounts if labels missed
    all_amounts = []
    # Find anything that looks like a decimal amount
    raw_amounts = re.findall(r"(\d+[\.,]\d{2})\s*(?:€|EUR)?", cleaned_text)
    for ra in raw_amounts:
        val = _clean_amount(ra)
        if val > 0: all_amounts.append((ra, val))

    # If missing, try to find in all_amounts
    if not total_ht_str and len(all_amounts) >= 2:
        total_ht_str = all_amounts[-3][0] if len(all_amounts) >= 3 else all_amounts[-2][0]
        total_ttc_str = all_amounts[-1][0]

    return {
        "company_name": company,
        "reference": get_val("REF", cleaned_text),
        "siret": [siret] if siret else [],
        "dates": [date_val] if date_val else [],
        "total_ht": total_ht_str,
        "tva_rate": "20", # Assumed default for simplification
        "tva_amount": tva_amount_str,
        "total_ttc": total_ttc_str,
    }