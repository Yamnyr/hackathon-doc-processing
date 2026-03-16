def check_inconsistencies(doc1, doc2):

    alerts = []

    if doc1["siren"] != doc2["siren"]:
        alerts.append("SIREN mismatch")

    return alerts