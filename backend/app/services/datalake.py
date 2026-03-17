"""
Data Lake service — Medallion architecture (Bronze → Silver → Gold).

Usage from pipeline modules
----------------------------
from backend.app.services.datalake import (
    generate_batch_id,
    generate_document_id,
    save_to_bronze,
    create_document_entry,
    save_to_silver,
    save_to_gold,
)
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.db.mongodb import get_db

# ---------------------------------------------------------------------------
# Folder layout
# ---------------------------------------------------------------------------

_LAYERS: dict[str, str] = {
    "bronze_raw":        "data/bronze/raw_docs",
    "bronze_meta":       "data/bronze/metadata",
    "silver_ocr":        "data/silver/ocr_text",
    "silver_extracted":  "data/silver/extracted_json",
    "silver_normalized": "data/silver/normalized",
    "gold_validated":    "data/gold/validated",
    "gold_anomalies":    "data/gold/anomalies",
    "gold_exports":      "data/gold/exports",
}


def init_datalake() -> None:
    """Create every Data Lake directory if it does not already exist."""
    for path in _LAYERS.values():
        os.makedirs(path, exist_ok=True)


# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------

def generate_document_id() -> str:
    return str(uuid.uuid4())


def generate_batch_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Bronze layer
# ---------------------------------------------------------------------------

def save_to_bronze(
    document_id: str,
    filename: str,
    file_bytes: bytes,
    batch_id: str,
) -> dict:
    """
    Write raw bytes to ``bronze/raw_docs`` and a JSON metadata sidecar to
    ``bronze/metadata``.

    Returns the metadata dict so the caller can forward it to
    ``create_document_entry``.
    """
    init_datalake()

    raw_path = os.path.join(_LAYERS["bronze_raw"], f"{document_id}_{filename}")
    with open(raw_path, "wb") as fh:
        fh.write(file_bytes)

    metadata: dict = {
        "document_id": document_id,
        "filename": filename,
        "file_path": raw_path,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "batch_id": batch_id,
        "status": "raw",
    }

    meta_path = os.path.join(_LAYERS["bronze_meta"], f"{document_id}.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, ensure_ascii=False)

    return metadata


def create_document_entry(metadata: dict, predicted_type: str = "unknown") -> None:
    """
    Insert one record into the MongoDB ``documents`` collection.

    Call this right after ``save_to_bronze``.
    """
    db = get_db()
    db["documents"].insert_one(
        {
            "document_id":  metadata["document_id"],
            "batch_id":     metadata["batch_id"],
            "filename":     metadata["filename"],
            "bronze_path":  metadata["file_path"],
            "uploaded_at":  metadata["uploaded_at"],
            "status":       metadata["status"],
            "predicted_type": predicted_type,
        }
    )


# ---------------------------------------------------------------------------
# Silver layer
# ---------------------------------------------------------------------------

def save_to_silver(
    document_id: str,
    batch_id: str,
    ocr_text: Optional[str] = None,
    extracted_data: Optional[dict] = None,
    normalized_data: Optional[dict] = None,
) -> dict:
    """
    Persist Silver-layer artefacts produced by the pipeline modules.

    Parameters
    ----------
    document_id:     UUID string for the document.
    batch_id:        UUID string for the upload batch.
    ocr_text:        Raw OCR string from ``ocr.extract_text()``.
    extracted_data:  Dict returned by ``extractor.extract_information()``.
    normalized_data: Any normalised/enriched version of extracted_data.

    Returns a dict mapping artefact type → file path for every written file.
    """
    init_datalake()

    paths: dict[str, str] = {}
    now = datetime.now(timezone.utc).isoformat()

    if ocr_text is not None:
        p = os.path.join(_LAYERS["silver_ocr"], f"{document_id}.txt")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(ocr_text)
        paths["ocr_path"] = p

    if extracted_data is not None:
        p = os.path.join(_LAYERS["silver_extracted"], f"{document_id}.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(extracted_data, fh, indent=2, ensure_ascii=False)
        paths["extracted_path"] = p

    if normalized_data is not None:
        p = os.path.join(_LAYERS["silver_normalized"], f"{document_id}.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(normalized_data, fh, indent=2, ensure_ascii=False)
        paths["normalized_path"] = p

    db = get_db()

    # Upsert extracted_data collection
    db["extracted_data"].update_one(
        {"document_id": document_id},
        {
            "$set": {
                "document_id":     document_id,
                "batch_id":        batch_id,
                "silver_path":     paths.get("extracted_path") or paths.get("ocr_path", ""),
                "normalized_data": normalized_data or {},
                "extracted_at":    now,
                **paths,
            }
        },
        upsert=True,
    )

    # Advance document status
    db["documents"].update_one(
        {"document_id": document_id},
        {"$set": {"status": "silver"}},
    )

    return paths


# ---------------------------------------------------------------------------
# Gold layer
# ---------------------------------------------------------------------------

def save_to_gold(
    batch_id: str,
    validated_records: Optional[list] = None,
    anomalies: Optional[list] = None,
) -> dict:
    """
    Persist Gold-layer artefacts (validated records and anomalies).

    Parameters
    ----------
    batch_id:           UUID string for the upload batch.
    validated_records:  List of validated supplier record dicts, each with
                        optional keys: supplier_name, siren, siret,
                        validated_documents.
    anomalies:          List of anomaly dicts, each with optional keys:
                        rule_code, message, severity, document_ids.

    Returns a dict mapping artefact type → file path for every written file.
    """
    init_datalake()

    paths: dict[str, str] = {}
    now = datetime.now(timezone.utc).isoformat()
    db = get_db()

    if validated_records is not None:
        p = os.path.join(_LAYERS["gold_validated"], f"{batch_id}.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(validated_records, fh, indent=2, ensure_ascii=False)
        paths["validated_path"] = p

        for record in validated_records:
            db["validated_records"].update_one(
                {"batch_id": batch_id},
                {
                    "$set": {
                        "batch_id":            batch_id,
                        "supplier_name":       record.get("supplier_name", ""),
                        "siren":               record.get("siren", ""),
                        "siret":               record.get("siret", ""),
                        "validated_documents": record.get("validated_documents", []),
                        "status":              "validated",
                        "validated_at":        now,
                    }
                },
                upsert=True,
            )

    if anomalies is not None:
        p = os.path.join(_LAYERS["gold_anomalies"], f"{batch_id}.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(anomalies, fh, indent=2, ensure_ascii=False)
        paths["anomalies_path"] = p

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

    # Advance batch document statuses to gold
    db["documents"].update_many(
        {"batch_id": batch_id},
        {"$set": {"status": "gold"}},
    )

    return paths
