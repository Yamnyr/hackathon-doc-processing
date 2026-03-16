import re

def extract_information(text):

    siren = re.findall(r"\b\d{9}\b", text)

    montant = re.findall(r"\d+[,.]\d{2}\s?€", text)

    return {
        "siren": siren,
        "montant": montant
    }