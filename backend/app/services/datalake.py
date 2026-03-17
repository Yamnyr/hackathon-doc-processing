"""
Data Lake service — Medallion architecture (Bronze → Silver → Gold).

Structure:
    data/bronze/   raw uploaded files
    data/silver/   OCR text files  (.txt)
    data/gold/     validated JSON  (.json)
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.db.mongodb import get_db

# ---------------------------------------------------------------------------
# Folder layout — 3 flat directories, no subfolders
# ---------------------------------------------------------------------------

BRONZE = "data/bronze"
SILVER = "data/silver"
GOLD   = "data/gold"


def init_datalake() -> None:
    """Create the 3 Data Lake directories if they do not already exist."""
    for path in (BRONZE, SILVER, GOLD):
        os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------

def generate_document_id() -> str:
    return str(uuid.uuid4())


def generate_batch_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Bronze layer — raw uploaded file
# ---------------------------------------------------------------------------

def save_to_bronze(
    document_id: str,
    filename: str,
    file_bytes: bytes,
    batch_id: str,
) -> dict:
    """
    Save the raw uploaded file directly into data/bronze/.
    Metadata is stored in MongoDB only (no sidecar file).

    Returns the metadata dict.
    """
    init_datalake()

    bronze_path = os.path.join(BRONZE, f"{document_id}_{filename}")
    with open(bronze_path, "wb") as fh:
        fh.write(file_bytes)

    return {
        "document_id": document_id,
        "filename":    filename,
        "file_path":   bronze_path,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "batch_id":    batch_id,
        "status":      "bronze",
    }


def create_document_entry(metadata: dict, predicted_type: str = "unknown") -> None:
    """Insert one record into the MongoDB ``documents`` collection."""
    db = get_db()
    db["documents"].insert_one(
        {
            "document_id":    metadata["document_id"],
            "batch_id":       metadata["batch_id"],
            "filename":       metadata["filename"],
            "bronze_path":    metadata["file_path"],
            "uploaded_at":    metadata["uploaded_at"],
            "status":         metadata["status"],
            "predicted_type": predicted_type,
        }
    )


# ---------------------------------------------------------------------------
# Silver layer — OCR text file
# ---------------------------------------------------------------------------

def save_to_silver(
    document_id: str,
    batch_id: str,
    ocr_text: Optional[str] = None,
    extracted_data: Optional[dict] = None,
    normalized_data: Optional[dict] = None,
) -> dict:
    """
    Save the OCR text into data/silver/{document_id}.txt.
    Extracted and normalized data are stored in MongoDB only.

    Returns a dict with the silver_path key.
    """
    init_datalake()

    paths: dict = {}
    now = datetime.now(timezone.utc).isoformat()

    if ocr_text is not None:
        silver_path = os.path.join(SILVER, f"{document_id}.txt")
        with open(silver_path, "w", encoding="utf-8") as fh:
            fh.write(ocr_text)
        paths["silver_path"] = silver_path

    db = get_db()
    db["extracted_data"].update_one(
        {"document_id": document_id},
        {
            "$set": {
                "document_id":     document_id,
                "batch_id":        batch_id,
                "silver_path":     paths.get("silver_path", ""),
                "extracted_data":  extracted_data  or {},
                "normalized_data": normalized_data or {},
                "extracted_at":    now,
            }
        },
        upsert=True,
    )

    db["documents"].update_one(
        {"document_id": document_id},
        {"$set": {"status": "silver"}},
    )

    return paths


# ---------------------------------------------------------------------------
# Gold layer — validated JSON file
# ---------------------------------------------------------------------------

def save_to_gold(
    batch_id: str,
    document_id: Optional[str] = None,
    validated_record: Optional[dict] = None,
    anomalies: Optional[list] = None,
) -> dict:
    """
    Save one validated record as data/gold/{document_id}.json.
    Anomalies are stored in MongoDB only.

    Returns a dict with the gold_path key.
    """
    init_datalake()

    paths: dict = {}
    now = datetime.now(timezone.utc).isoformat()
    db  = get_db()

    if validated_record is not None and document_id is not None:
        p = os.path.join(GOLD, f"{document_id}.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(validated_record, fh, indent=2, ensure_ascii=False)
        paths["gold_path"] = p

        db["validated_records"].update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "document_id":   document_id,
                    "batch_id":      batch_id,
                    "supplier_name": validated_record.get("supplier_name", ""),
                    "siren":         validated_record.get("siren", ""),
                    "siret":         validated_record.get("siret", ""),
                    "doc_type":      validated_record.get("doc_type", ""),
                    "montants":      validated_record.get("montants", []),
                    "status":        "validated",
                    "validated_at":  now,
                }
            },
            upsert=True,
        )

    if anomalies:
        for anomaly in anomalies:
            db["anomalies"].insert_one(
                {
                    "anomaly_id":   str(uuid.uuid4()),
                    "batch_id":     batch_id,
                    "rule_code":    anomaly.get("rule_code", "UNKNOWN"),
                    "message":      anomaly.get("message", ""),
                    "severity":     anomaly.get("severity", "medium"),
                    "document_ids": anomaly.get("document_ids", []),
                    "detected_at":  now,
                }
            )

    if document_id:
        db["documents"].update_one(
            {"document_id": document_id},
            {"$set": {"status": "gold"}},
        )

    return paths
