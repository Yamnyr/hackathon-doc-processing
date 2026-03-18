"""
Full Data Lake integration test.

Run:
    $env:PYTHONPATH = "."
    $env:MONGO_URI  = "mongodb://localhost:27017/hackathon"
    python test_datalake_full.py
"""

import json, os, sys
sys.path.insert(0, ".")

from backend.app.services.datalake import (
    create_document_entry, generate_batch_id, generate_document_id,
    save_to_raw, save_to_clean, save_to_curated,
)
from backend.app.db.mongodb import get_db

SEP = "-" * 55

def ok(msg):   print(f"  [OK]  {msg}")
def fail(msg): print(f"  [FAIL] {msg}"); sys.exit(1)
def check(label, condition): (ok if condition else fail)(label)


# ── RAW ───────────────────────────────────────────────────────────────────
def test_raw():
    print(f"\n{SEP}\n RAW — fichier brut uploadé\n{SEP}")

    batch_id = generate_batch_id()
    doc_id   = generate_document_id()
    content  = b"facture n 001  SIREN 123456789  montant 1500,00 EUR"

    meta = save_to_raw(doc_id, "test_facture.txt", content, batch_id)

    check("Fichier sauvegardé dans data/raw/",
          os.path.exists(meta["file_path"]))
    check("status == 'raw'", meta["status"] == "raw")

    create_document_entry(meta, predicted_type="facture")
    doc = get_db()["documents"].find_one({"document_id": doc_id})
    check("Enregistrement dans MongoDB (documents)", doc is not None)
    check("predicted_type stocké", doc["predicted_type"] == "facture")

    print(f"\n  batch_id    : {batch_id}")
    print(f"  document_id : {doc_id}")
    print(f"  fichier     : {meta['file_path']}")
    return doc_id, batch_id


# ── CLEAN ─────────────────────────────────────────────────────────────────
def test_clean(doc_id, batch_id):
    print(f"\n{SEP}\n CLEAN — texte OCR\n{SEP}")

    ocr = "facture n 001  SIREN 123456789  montant 1500,00 EUR"

    paths = save_to_clean(
        doc_id, batch_id,
        ocr_text=ocr,
        extracted_data={"siren": ["123456789"], "montant": ["1500,00 EUR"]},
        normalized_data={"siren": "123456789", "amount_eur": 1500.0},
    )

    clean_file = f"data/clean/{doc_id}.txt"
    check("Fichier OCR sauvegardé dans data/clean/",
          os.path.exists(clean_file))

    with open(clean_file) as f:
        check("Contenu OCR correct", "123456789" in f.read())

    rec = get_db()["extracted_data"].find_one({"document_id": doc_id})
    check("Enregistrement dans MongoDB (extracted_data)", rec is not None)
    check("normalized_data stocké", rec["normalized_data"]["amount_eur"] == 1500.0)

    doc = get_db()["documents"].find_one({"document_id": doc_id})
    check("Status avancé à 'clean'", doc["status"] == "clean")

    print(f"  fichier OCR : {clean_file}")


# ── CURATED ───────────────────────────────────────────────────────────────
def test_curated(doc_id, batch_id):
    print(f"\n{SEP}\n CURATED — JSON validé\n{SEP}")

    paths = save_to_curated(
        batch_id,
        document_id=doc_id,
        validated_record={
            "supplier_name":       "ACME SAS",
            "siren":               "123456789",
            "siret":               "12345678900010",
        },
        anomalies=[{
            "rule_code":    "SIREN_MISMATCH",
            "message":      "SIREN diffère entre deux documents du batch",
            "severity":     "high",
            "document_ids": [doc_id],
        }],
    )

    curated_file = f"data/curated/{doc_id}.json"
    check("JSON validé sauvegardé dans data/curated/",
          os.path.exists(curated_file))

    with open(curated_file) as f:
        data = json.load(f)
    check("SIREN présent dans le JSON curated", data["siren"] == "123456789")

    val  = get_db()["validated_records"].find_one({"batch_id": batch_id})
    anom = get_db()["anomalies"].find_one({"batch_id": batch_id})
    check("Enregistrement dans MongoDB (validated_records)", val is not None)
    check("Anomalie dans MongoDB (anomalies)", anom is not None)
    check("rule_code correct", anom["rule_code"] == "SIREN_MISMATCH")

    doc = get_db()["documents"].find_one({"document_id": doc_id})
    check("Status avancé à 'curated'", doc["status"] == "curated")

    print(f"  fichier curated : {curated_file}")


# ── ARBRE FINAL ─────────────────────────────────────────────────────────────
def show_tree():
    print(f"\n{SEP}\n STRUCTURE DU DATA LAKE\n{SEP}")
    for layer in ("data/raw", "data/clean", "data/curated"):
        files = [f for f in os.listdir(layer) if f != ".gitkeep"]
        print(f"  {layer}/  ({len(files)} fichier(s))")
        for f in files:
            print(f"    {f}")

def show_mongo():
    print(f"\n{SEP}\n COLLECTIONS MONGODB\n{SEP}")
    db = get_db()
    for col in ["documents", "extracted_data", "validated_records", "anomalies"]:
        print(f"  {col:<22} {db[col].count_documents({})} document(s)")


# ── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== Data Lake — Test d'intégration complet ===")
    doc_id, batch_id = test_raw()
    test_clean(doc_id, batch_id)
    test_curated(doc_id, batch_id)
    show_tree()
    show_mongo()
    print(f"\n{'=' * 55}")
    print("  Tous les tests passés. Data Lake opérationnel.")
    print(f"{'=' * 55}\n")
