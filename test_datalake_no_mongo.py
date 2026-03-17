"""
Smoke-test the Data Lake file system layer without MongoDB or Docker.

Run from the project root:
    python test_datalake_no_mongo.py
"""

import json
import os
import sys
import types
import unittest.mock as mock

# ---------------------------------------------------------------------------
# Stub out pymongo so the import doesn't crash when it's not installed
# ---------------------------------------------------------------------------
pymongo_stub = types.ModuleType("pymongo")


class _FakeCollection:
    def insert_one(self, doc): pass
    def update_one(self, *a, **kw): pass
    def update_many(self, *a, **kw): pass


class _FakeDB:
    def __getitem__(self, name):
        return _FakeCollection()


class _FakeClient:
    def __getitem__(self, name):
        return _FakeDB()


pymongo_stub.MongoClient = lambda *a, **kw: _FakeClient()
sys.modules.setdefault("pymongo", pymongo_stub)

# ---------------------------------------------------------------------------
# Now import the real service (MongoDB calls are no-ops via the stub)
# ---------------------------------------------------------------------------
sys.path.insert(0, ".")

from backend.app.services.datalake import (
    generate_batch_id,
    generate_document_id,
    save_to_bronze,
    create_document_entry,
    save_to_silver,
    save_to_gold,
)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_bronze():
    batch_id = generate_batch_id()
    doc_id   = generate_document_id()

    meta = save_to_bronze(doc_id, "test_invoice.txt", b"facture content 123456789", batch_id)

    assert os.path.exists(meta["file_path"]), "Raw file not created"
    assert os.path.exists(f"data/bronze/metadata/{doc_id}.json"), "Metadata sidecar not created"

    with open(f"data/bronze/metadata/{doc_id}.json") as f:
        saved = json.load(f)

    assert saved["document_id"] == doc_id
    assert saved["batch_id"]    == batch_id
    assert saved["status"]      == "raw"

    create_document_entry(meta, predicted_type="facture")

    print(f"  [OK] Bronze  doc_id={doc_id[:8]}...  batch_id={batch_id[:8]}...")
    return doc_id, batch_id


def test_silver(doc_id, batch_id):
    paths = save_to_silver(
        doc_id, batch_id,
        ocr_text="facture n°001 SIREN 123456789 montant 100,00 €",
        extracted_data={"siren": ["123456789"], "montant": ["100,00 €"]},
        normalized_data={"siren": "123456789", "amount_eur": 100.0},
    )

    assert os.path.exists(paths["ocr_path"]),        "OCR text file not created"
    assert os.path.exists(paths["extracted_path"]),  "Extracted JSON not created"
    assert os.path.exists(paths["normalized_path"]), "Normalized JSON not created"

    with open(paths["extracted_path"]) as f:
        data = json.load(f)
    assert data["siren"] == ["123456789"]

    print(f"  [OK] Silver  ocr={paths['ocr_path']}")


def test_gold(batch_id, doc_id):
    paths = save_to_gold(
        batch_id,
        validated_records=[{
            "supplier_name":       "ACME SAS",
            "siren":               "123456789",
            "siret":               "12345678900010",
            "validated_documents": [doc_id],
        }],
        anomalies=[{
            "rule_code":    "SIREN_MISMATCH",
            "message":      "SIREN differs between documents",
            "severity":     "high",
            "document_ids": [doc_id],
        }],
    )

    assert os.path.exists(paths["validated_path"]),  "Validated JSON not created"
    assert os.path.exists(paths["anomalies_path"]),  "Anomalies JSON not created"

    print(f"  [OK] Gold    validated={paths['validated_path']}")


def show_tree():
    print("\n--- Data Lake file tree ---")
    for root, dirs, files in os.walk("data"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        level = root.replace("data", "").count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        for f in files:
            if f != ".gitkeep":
                print(f"{indent}  {f}")


if __name__ == "__main__":
    print("\n=== Data Lake smoke test (no MongoDB / no Docker) ===\n")
    doc_id, batch_id = test_bronze()
    test_silver(doc_id, batch_id)
    test_gold(batch_id, doc_id)
    show_tree()
    print("\nAll tests passed.")
