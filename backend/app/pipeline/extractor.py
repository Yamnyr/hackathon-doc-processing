import re

def extract_information(text: str) -> dict:
    # 1. Basic cleaning
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)

    # 2. SIRET Extraction (Robust to spaces)
    # Remove all spaces and find exactly 14 digits
    siret_search_text = re.sub(r"\s+", "", cleaned_text)
    siret_matches = re.findall(r"\d{14}", siret_search_text)
    siret = siret_matches[0] if siret_matches else None

    # 3. Date Extraction
    # Format dd/mm/yyyy with flexible spaces
    date_matches = re.findall(r"\d{2}\s*/\s*\d{2}\s*/\s*\d{4}", cleaned_text)
    date_val = date_matches[0].replace(" ", "") if date_matches else None

    # 4. Key-Value Helper
    def get_val(key):
        # Match "KEY: VALUE" or "KEY - VALUE", handling decimals and spaces
        match = re.search(rf"{key}\s*[:\-]*\s*([\d\s\.,]+)", cleaned_text, re.IGNORECASE)
        if match:
            # Cleanup for numeric extraction
            val = match.group(1).replace(" ", "").replace(",", ".")
            return val.rstrip('.')
        return None

    # 5. Specialized TVA Extraction (ignore percentage in parentheses)
    # Specifically matches "TVA (20%): 236.4"
    # Group 1 captures the actual amount
    tva_match = re.search(r"TVA\s*(?:\(.*?\))?\s*[:\-]*\s*([\d\s\.,]+)", cleaned_text, re.IGNORECASE)
    tva_str = None
    if tva_match:
        tva_str = tva_match.group(1).replace(" ", "").replace(",", ".").rstrip('.')

    # 6. Company Name Helper (Simple string after COMPANY:)
    company_match = re.search(r"COMPANY\s*[:\-]*\s*([^\n\r]+)", cleaned_text, re.IGNORECASE)
    company = company_match.group(1).strip() if company_match else "Inconnu"

    results = {
        "siret": siret,
        "date": date_val,
        "total_ht": get_val("TOTAL HT"),
        "tva": tva_str,
        "total_ttc": get_val("TOTAL TTC"),
        "company_name": company
    }
    
    # Return mapping for compatibility with pipeline
    return {
        "company_name": results["company_name"],
        "siret": [results["siret"]] if results["siret"] else [],
        "dates": [results["date"]] if results["date"] else [],
        "total_ht": results["total_ht"],
        "tva_amount": results["tva"],
        "total_ttc": results["total_ttc"],
    }