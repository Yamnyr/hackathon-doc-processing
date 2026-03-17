def classify_document(text: str) -> str:
    text = text.lower()

    scores = {
        "facture": 0,
        "devis": 0,
        "attestation": 0,
        "rib": 0,
    }

    # mots-clés pondérés
    weighted_keywords = {
        "facture": {
            "facture": 5,
            "net à payer": 3,
            "montant ttc": 2,
            "total ttc": 1,
            "tva": 1,
        },
        "devis": {
            "devis": 5,
            "ref: dev": 3,
            "ref : dev": 3,
            "n° : dev": 3,
            "validité": 2,
            "total ht": 1,
            "total ttc": 1,
            "tva": 1,
        },
        "attestation": {
            "attestation": 5,
            "urssaf": 3,
            "vigilance": 3,
            "certifie": 2,
        },
        "rib": {
            "iban": 5,
            "bic": 4,
            "rib": 4,
            "relevé d'identité bancaire": 5,
        },
    }

    for doc_type, keywords in weighted_keywords.items():
        for word, weight in keywords.items():
            if word in text:
                scores[doc_type] += weight

    # priorité forte si le titre du document est visible
    if "devis" in text[:300]:
        scores["devis"] += 10
    if "facture" in text[:300]:
        scores["facture"] += 10
    if "attestation" in text[:300]:
        scores["attestation"] += 10

    best_type = max(scores, key=scores.get)

    if scores[best_type] == 0:
        return "unknown"

    return best_type