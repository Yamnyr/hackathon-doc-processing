def classify_document(text):

    text = text.lower()

    if "facture" in text:
        return "facture"

    if "devis" in text:
        return "devis"

    if "attestation" in text:
        return "attestation"

    return "unknown"