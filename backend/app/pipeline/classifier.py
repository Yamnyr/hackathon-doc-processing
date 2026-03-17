def classify_document(text: str) -> str:
    text = text.lower()

    scores = {
        "facture": 0,
        "devis": 0,
        "attestation": 0,
        "rib": 0,
    }

    keywords = {
        "facture": [
            "facture",
            "net à payer",
            "montant ttc",
            "total ttc",
            "numéro de facture",
        ],
        "devis": [
            "devis",
            "n° : dev",
            "ref: dev",
            "ref : dev",
            "validité",
            "total ht",
        ],
        "attestation": [
            "attestation",
            "urssaf",
            "vigilance",
            "date d'expiration",
            "certifie",
        ],
        "rib": [
            "iban",
            "bic",
            "rib",
            "relevé d'identité bancaire",
        ],
    }

    for doc_type, words in keywords.items():
        for word in words:
            if word in text:
                scores[doc_type] += 1

    best_type = max(scores, key=scores.get)

    if scores[best_type] == 0:
        return "unknown"

    return best_type