import re

from fastapi import APIRouter, UploadFile, File

from backend.app.pipeline.classifier import classify_document
from backend.app.pipeline.extractor import extract_information
from backend.app.pipeline.validator import check_inconsistencies
from backend.app.services.datalake import (
    create_document_entry,
    generate_batch_id,
    generate_document_id,
    init_datalake,
    save_to_bronze,
    save_to_silver,
    save_to_gold,
)

router = APIRouter()
init_datalake()


def _extract_text(file_path: str) -> str:
    """
    Extract raw text from a file.
    - PDF        → pdfplumber (text layer, no OCR needed)
    - Image/WebP → Pillow converts to numpy array → pytesseract OCR
    """
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        import pdfplumber
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text.strip()

    # Images: use Pillow to open any format (JPG, PNG, WEBP, TIFF, BMP …)
    # then convert to a numpy array for pytesseract
    try:
        import numpy as np
        import pytesseract
        from PIL import Image
        import cv2

        # Hardcode Tesseract path so it works regardless of system PATH
        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        pil_img   = Image.open(file_path).convert("RGB")
        img_array = np.array(pil_img)
        gray      = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        return pytesseract.image_to_string(gray)

    except pytesseract.TesseractNotFoundError:
        print("[WARN] Tesseract not found at C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
        return ""
    except Exception as e:
        print(f"[WARN] image OCR failed for {file_path}: {e}")
        return ""


_DOC_KEYWORDS = {"devis", "facture", "attestation", "invoice", "unknown"}


def _normalize(text: str, fields: dict, doc_type: str) -> dict:
    """
    Build normalized data from raw extracted fields + OCR text.

    Handles:
    - SIRET label followed by 9 or 14 digits (with or without spaces)
    - 'DE: Supplier A: Client' pattern from image OCR
    - Skips doc-type keywords when looking for supplier name
    """
    # --- Extract digits after SIRET: label (9 or 14 digits, spaces allowed) -
    siret_match = re.search(r"SIRET\s*:?\s*([\d][\d\s]{7,17}[\d])", text, re.IGNORECASE)
    siret = ""
    siren = ""
    if siret_match:
        digits = re.sub(r"\s+", "", siret_match.group(1))
        if len(digits) == 14:
            siret = digits
            siren = digits[:9]
        elif len(digits) == 9:
            # OCR truncated to SIREN only
            siren = digits
        elif len(digits) > 9:
            siren = digits[:9]

    # Fallback: extractor regex found a 9-digit number directly
    if not siren and fields["siren"]:
        siren = fields["siren"][0]

    # --- Supplier name: try 'DE: Name A:' pattern first (image OCR format) --
    supplier_name = ""
    de_match = re.search(r"DE\s*:\s*(.+?)\s+A\s*:", text, re.IGNORECASE)
    if de_match:
        supplier_name = de_match.group(1).strip()
    else:
        # Fallback: first non-empty line that is not a doc-type keyword
        for line in text.splitlines():
            line = line.strip()
            if line and line.lower() not in _DOC_KEYWORDS:
                supplier_name = line
                break

    return {
        "doc_type":      doc_type,
        "supplier_name": supplier_name,
        "siren":         siren,
        "siret":         siret,
        "montants":      fields["montant"],
    }


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """
    Full pipeline per upload:
      1. Bronze  — save raw file
      2. Silver  — OCR / text extraction + classification + field extraction
      3. Gold    — cross-document validation + anomaly detection
    """
    batch_id   = generate_batch_id()
    results    = []
    extracted  = {}   # document_id → extract_information() output (for Gold validation)

    # ── BRONZE + SILVER ──────────────────────────────────────────────────────
    for file in files:
        document_id = generate_document_id()
        file_bytes  = await file.read()

        # Bronze
        metadata = save_to_bronze(document_id, file.filename, file_bytes, batch_id)

        # Text extraction
        try:
            text = _extract_text(metadata["file_path"])
        except Exception as e:
            text = ""
            print(f"[WARN] text extraction failed for {file.filename}: {e}")

        # Classification + extraction
        doc_type   = classify_document(text)
        fields     = extract_information(text)
        normalized = _normalize(text, fields, doc_type)

        # Silver
        save_to_silver(
            document_id, batch_id,
            ocr_text=text,
            extracted_data=fields,
            normalized_data=normalized,
        )

        # MongoDB document entry
        create_document_entry(metadata, predicted_type=doc_type)

        extracted[document_id] = {"fields": fields, "normalized": normalized}
        results.append({
            "document_id":   document_id,
            "filename":      file.filename,
            "batch_id":      batch_id,
            "doc_type":      doc_type,
            "supplier_name": normalized["supplier_name"],
            "siren":         normalized["siren"],
            "siret":         normalized["siret"],
            "montants":      normalized["montants"],
            "bronze_path":   metadata["file_path"],
            "silver_path":   f"data/silver/{document_id}.txt",
            "status":        "silver",
        })

    # ── GOLD — cross-document validation ────────────────────────────────────
    anomalies = []
    doc_ids   = list(extracted.keys())

    for i in range(len(doc_ids)):
        for j in range(i + 1, len(doc_ids)):
            alerts = check_inconsistencies(
                extracted[doc_ids[i]]["fields"],
                extracted[doc_ids[j]]["fields"],
            )
            for alert in alerts:
                anomalies.append({
                    "rule_code":    "SIREN_MISMATCH",
                    "message":      alert,
                    "severity":     "high",
                    "document_ids": [doc_ids[i], doc_ids[j]],
                })

    # ── GOLD — one file per document ────────────────────────────────────────
    for result in results:
        did  = result["document_id"]
        data = extracted[did]
        record = {
            "document_id":   did,
            "batch_id":      batch_id,
            "supplier_name": data["normalized"]["supplier_name"],
            "siren":         data["normalized"]["siren"],
            "siret":         data["normalized"]["siret"],
            "doc_type":      data["normalized"]["doc_type"],
            "montants":      data["normalized"]["montants"],
            "anomalies":     [a for a in anomalies if did in a["document_ids"]],
            "status":        "validated",
        }
        gold_paths = save_to_gold(batch_id, document_id=did, validated_record=record)
        result["gold_path"] = gold_paths.get("gold_path", "")
        result["status"]    = "gold"

    # ── RESPONSE ─────────────────────────────────────────────────────────────
    return {
        "batch_id":  batch_id,
        "anomalies": anomalies,
        "documents": results,
    }
