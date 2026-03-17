import re


def _to_float(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).replace("€", "").replace("%", "").replace(" ", "").replace(",", ".").strip()

    try:
        return float(value)
    except ValueError:
        return None


def validate_document(doc: dict) -> dict:
    issues = []

    document_type = doc.get("document_type")
    extracted = doc.get("extracted_data", {})

    siret_list = extracted.get("siret", [])
    dates = extracted.get("dates", [])
    total_ht = _to_float(extracted.get("total_ht"))
    tva_rate = _to_float(extracted.get("tva_rate"))
    tva_amount = _to_float(extracted.get("tva_amount"))
    total_ttc = _to_float(extracted.get("total_ttc"))

    if not document_type or document_type == "unknown":
        issues.append("Type de document inconnu")

    if not siret_list:
        issues.append("SIRET manquant")
    else:
        for siret in siret_list:
            if not re.fullmatch(r"\d{14}", siret):
                issues.append(f"SIRET invalide : {siret}")

    if not dates:
        issues.append("Date manquante")

    if document_type in ["devis", "facture"]:
        if total_ht is None:
            issues.append("Total HT manquant ou invalide")
        if tva_amount is None:
            issues.append("Montant TVA manquant ou invalide")
        if total_ttc is None:
            issues.append("Total TTC manquant ou invalide")

        if total_ht is not None and tva_amount is not None and total_ttc is not None:
            expected_ttc = round(total_ht + tva_amount, 2)
            observed_ttc = round(total_ttc, 2)

            if abs(expected_ttc - observed_ttc) > 0.01:
                issues.append(
                    f"Incohérence montants : HT + TVA = {expected_ttc}, mais TTC = {observed_ttc}"
                )

        # Vérification bonus du taux TVA si présent
        if total_ht is not None and tva_rate is not None and tva_amount is not None:
            expected_tva_amount = round(total_ht * (tva_rate / 100), 2)
            observed_tva_amount = round(tva_amount, 2)

            if abs(expected_tva_amount - observed_tva_amount) > 0.01:
                issues.append(
                    f"Incohérence TVA : HT x taux = {expected_tva_amount}, mais TVA = {observed_tva_amount}"
                )

    return {
        "is_valid": len(issues) == 0,
        "issues": issues
    }


def check_inconsistencies(doc1: dict, doc2: dict) -> list:
    alerts = []

    extracted1 = doc1.get("extracted_data", {})
    extracted2 = doc2.get("extracted_data", {})

    siret1 = extracted1.get("siret", [])
    siret2 = extracted2.get("siret", [])

    company1 = extracted1.get("company_name")
    company2 = extracted2.get("company_name")

    if siret1 and siret2 and set(siret1) != set(siret2):
        alerts.append("SIRET mismatch entre les deux documents")

    if company1 and company2 and company1.strip().lower() != company2.strip().lower():
        alerts.append("Nom d'entreprise différent entre les deux documents")

    return alerts