import os
from datetime import datetime, date
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/hackathon")
DB_NAME = "hackathon"
COLLECTION_NAME = "companies"

try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = mongo_client[DB_NAME]
    companies_collection = db[COLLECTION_NAME]
except Exception as e:
    print(f"Erreur critique d'initialisation MongoDB : {e}")
    companies_collection = None

def get_known_sirens() -> set:
    if companies_collection is None:
        print("Avertissement : Base de données inaccessible. Validation SIREN ignorée ou faussée.")
        return set()
        
    try:
        cursor = companies_collection.find({"siren": {"$exists": True}}, {"siren": 1, "_id": 0})
        return set(doc["siren"] for doc in cursor if doc.get("siren"))
    except Exception as e:
        print(f"Erreur lors de la lecture des SIREN : {e}")
        return set()

def detect_anomalies(dossier_data: list) -> list:
    sirens_presents = set()
    known_siren_db = get_known_sirens()
    dossier_anomalies = []
    
    for doc in dossier_data:
        doc_anomalies = []
        
        doc_type = doc.get("doc_type")
        siren = doc.get("siren")
        siret = doc.get("siret")
        
        if siren: 
            sirens_presents.add(siren)
        if siret:
            if len(siret) == 14:
                sirens_presents.add(siret[:9])
            else:
                doc_anomalies.append(f"Format SIRET invalide : {siret}")

        doc_date_str = doc.get("document_date")
        if doc_date_str:
            try:
                doc_date = datetime.strptime(doc_date_str, "%Y-%m-%d").date()
                today = date.today()
                delta_days = (today - doc_date).days
                
                if delta_days < 0:
                    doc_anomalies.append(f"Incohérence temporelle : La date ({doc_date_str}) est dans le futur.")
                
                if doc_type == "Attestation URSSAF" and delta_days > 180:
                    doc_anomalies.append(f"Document expiré : L'attestation ({doc_date_str}) a plus de 6 mois.")
                    
            except ValueError:
                doc_anomalies.append(f"Format de date corrompu : {doc_date_str}")

        if doc_type == "Facture":
            ttc = doc.get("total_amount_ttc")
            ht = doc.get("total_amount_ht")
            tva = doc.get("tax_amount")
            
            if ttc is not None and ht is not None and tva is not None:
                if abs(ttc - (ht + tva)) > 0.05:
                    doc_anomalies.append(f"Erreur d'addition : {ht} + {tva} != {ttc}")
                
                tva_theorique = ht * 0.20
                if abs(tva - tva_theorique) > 0.05:
                    doc_anomalies.append(f"Fraude TVA : {tva} ne correspond pas à 20% de {ht}")

        doc["local_errors"] = doc_anomalies

    if len(sirens_presents) > 1:
        dossier_anomalies.append(f"Incohérence majeure (Dossier multi-entités) : {sirens_presents}")
        
    for s in sirens_presents:
        if s not in known_siren_db:
            dossier_anomalies.append(f"Fournisseur inconnu (SIREN {s} absent de la base MongoDB)")

    for doc in dossier_data:
        final_errors = doc.pop("local_errors") + dossier_anomalies
        
        if final_errors:
            doc["status"] = "Anomalie"
            doc["anomaly_reason"] = " | ".join(final_errors)
        else:
            doc["status"] = "Valide"
            doc["anomaly_reason"] = "Aucune"
            
    return dossier_data