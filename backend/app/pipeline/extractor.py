import re


def _first_or_none(matches):
    return matches[0] if matches else None


def extract_information(text: str) -> dict:
    siret_matches = re.findall(r"\b\d{14}\b", text)
    siren_matches = re.findall(r"\b\d{9}\b", text)

    date_matches = re.findall(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", text)

    total_ht_matches = re.findall(
        r"total\s*ht[:\s]*([0-9]+(?:[.,][0-9]{2})?\s?€?)",
        text,
        flags=re.IGNORECASE
    )

    total_ttc_matches = re.findall(
        r"total\s*ttc[:\s]*([0-9]+(?:[.,][0-9]{2})?\s?€?)",
        text,
        flags=re.IGNORECASE
    )

    # TVA pourcentage : ex "TVA (20%)"
    tva_rate_matches = re.findall(
        r"tva\s*\(?\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*%?\)?",
        text,
        flags=re.IGNORECASE
    )

    # TVA montant : ex "TVA (20%): 2866.80€"
    tva_amount_matches = re.findall(
        r"tva[^\n:]*[:\s]+([0-9]+(?:[.,][0-9]{2})?\s?€)",
        text,
        flags=re.IGNORECASE
    )

    ref_matches = re.findall(
        r"(?:ref|n°)\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        text,
        flags=re.IGNORECASE
    )

    company_lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            company_lines.append(line)

    company_name = company_lines[0] if company_lines else None

    return {
        "company_name": company_name,
        "reference": _first_or_none(ref_matches),
        "siren": list(set(siren_matches)),
        "siret": list(set(siret_matches)),
        "dates": list(set(date_matches)),
        "total_ht": _first_or_none(total_ht_matches),
        "tva_rate": _first_or_none(tva_rate_matches),
        "tva_amount": _first_or_none(tva_amount_matches),
        "total_ttc": _first_or_none(total_ttc_matches),
    }