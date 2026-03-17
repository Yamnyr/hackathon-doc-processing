"""
Full Data Lake integration test — requires MongoDB running on localhost:27017.

Run from the project root:
    $env:PYTHONPATH = "."
    $env:MONGO_URI  = "mongodb://localhost:27017/hackathon"
    python test_datalake_full.py
"""

import json
import os
import sys

sys.path.insert(0, ".")

from backend.app.services.datalake import (
    create_document_entry,
    generate_batch_id,
    generate_document_id,
    save_to_bronze,
    save_to_gold,
    save_to_silver,
)
from backend.app.db.mongodb import get_db

SEP = "-" * 55


def ok(msg):
    print(f"  [OK]  {msg}")


def check(label, condition, detail=""):
    if not condition:
        print(f"  [FAIL] {label}  {detail}")
        sys.exit(1)
    ok(label)


# ---------------------------------------------------------------------------
# 1. BRONZE
# ---------------------------------------------------------------------------
def test_bronze():
    print(f"\n{SEP}\n BRONZE LAYER\n{SEP}")

    batch_id = generate_batch_id()
    doc_id   = generate_document_id()
    content  = b"facture n 001  SIREN 123456789  montant 1500,00 EUR"

    meta = save_to_bronze(doc_id, "test_facture.txt", content, batch_id)

    # File on disk
    check("Raw file written to bronze/raw_docs",
          os.path.exists(meta["file_path"]))

    # Metadata sidecar
    meta_path = f"data/bronze/metadata/{doc_id}.json"
    check("Metadata sidecar written to bronze/metadata",
          os.path.exists(meta_path))

    with open(meta_path) as f:
        saved = json.load(f)
    check("document_id in sidecar",  saved["document_id"] == doc_id)
    check("batch_id in sidecar",     saved["batch_id"]    == batch_id)
    check("status == 'raw'",         saved["status"]      == "raw")

    # MongoDB
    create_document_entry(meta, predicted_type="facture")
    db  = get_db()
    doc = db["documents"].find_one({"document_id": doc_id})
    check("Record inserted in MongoDB documents collection", doc is not None)
    check("predicted_type stored",   doc["predicted_type"] == "facture")

    print(f"\n  batch_id    : {batch_id}")
    print(f"  document_id : {doc_id}")
    return doc_id, batch_id


# ---------------------------------------------------------------------------
# 2. SILVER
# ---------------------------------------------------------------------------
def test_silver(doc_id, batch_id):
    print(f"\n{SEP}\n SILVER LAYER\n{SEP}")

    ocr_text   = "facture n 001  SIREN 123456789  montant 1500,00 EUR"
    extracted  = {"siren": ["123456789"], "montant": ["1500,00 EUR"]}
    normalized = {"siren": "123456789", "amount_eur": 1500.0, "doc_type": "facture"}

    paths = save_to_silver(
        doc_id, batch_id,
        ocr_text=ocr_text,
        extracted_data=extracted,
        normalized_data=normalized,
    )

    # Files on disk
    check("OCR text file in silver/ocr_text",
          os.path.exists(paths["ocr_path"]))
    check("Extracted JSON in silver/extracted_json",
          os.path.exists(paths["extracted_path"]))
    check("Normalized JSON in silver/normalized",
          os.path.exists(paths["normalized_path"]))

    # Content check
    with open(paths["extracted_path"]) as f:
        data = json.load(f)
    check("Extracted SIREN correct", data["siren"] == ["123456789"])

    # MongoDB
    db  = get_db()
    rec = db["extracted_data"].find_one({"document_id": doc_id})
    check("Record upserted in MongoDB extracted_data collection", rec is not None)
    check("normalized_data stored in MongoDB", rec["normalized_data"]["amount_eur"] == 1500.0)

    # Status advanced
    doc = db["documents"].find_one({"document_id": doc_id})
    check("Document status advanced to 'silver'", doc["status"] == "silver")


# ---------------------------------------------------------------------------
# 3. GOLD
# ---------------------------------------------------------------------------
def test_gold(doc_id, batch_id):
    print(f"\n{SEP}\n GOLD LAYER\n{SEP}")

    validated = [{
        "supplier_name":       "ACME SAS",
        "siren":               "123456789",
        "siret":               "12345678900010",
        "validated_documents": [doc_id],
    }]
    anomalies = [{
        "rule_code":    "SIREN_MISMATCH",
        "message":      "SIREN differs between documents in batch",
        "severity":     "high",
        "document_ids": [doc_id],
    }]

    paths = save_to_gold(batch_id, validated_records=validated, anomalies=anomalies)

    # Files on disk
    check("Validated JSON in gold/validated",
          os.path.exists(paths["validated_path"]))
    check("Anomalies JSON in gold/anomalies",
          os.path.exists(paths["anomalies_path"]))

    # MongoDB
    db  = get_db()
    val = db["validated_records"].find_one({"batch_id": batch_id})
    check("Record upserted in MongoDB validated_records collection", val is not None)
    check("SIREN stored in validated_records", val["siren"] == "123456789")

    anom = db["anomalies"].find_one({"batch_id": batch_id})
    check("Anomaly inserted in MongoDB anomalies collection", anom is not None)
    check("rule_code stored", anom["rule_code"] == "SIREN_MISMATCH")
    check("severity stored",  anom["severity"]  == "high")

    # Status advanced to gold
    doc = db["documents"].find_one({"document_id": doc_id})
    check("Document status advanced to 'gold'", doc["status"] == "gold")


# ---------------------------------------------------------------------------
# 4. Summary tree
# ---------------------------------------------------------------------------
def show_tree():
    print(f"\n{SEP}\n DATA LAKE FILE TREE\n{SEP}")
    for root, dirs, files in os.walk("data"):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        level   = root.replace("data", "").count(os.sep)
        indent  = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        for fname in sorted(files):
            if fname != ".gitkeep":
                print(f"{indent}  {fname}")


def show_mongo_summary():
    print(f"\n{SEP}\n MONGODB COLLECTIONS\n{SEP}")
    db = get_db()
    for col in ["documents", "extracted_data", "validated_records", "anomalies"]:
        count = db[col].count_documents({})
        print(f"  {col:<22} {count} document(s)")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n=== Data Lake — Full Integration Test ===")
    doc_id, batch_id = test_bronze()
    test_silver(doc_id, batch_id)
    test_gold(doc_id, batch_id)
    show_tree()
    show_mongo_summary()
    print(f"\n{'=' * 55}")
    print("  All tests passed. Data Lake is fully operational.")
    print(f"{'=' * 55}\n")
