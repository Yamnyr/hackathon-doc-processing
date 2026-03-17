from fastapi import APIRouter, UploadFile, File
import os
import json

from backend.app.pipeline.ocr import extract_text
from backend.app.pipeline.extractor import extract_information
from backend.app.pipeline.classifier import classify_document
from backend.app.pipeline.validator import validate_document, check_inconsistencies

router = APIRouter()

RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"
CURATED_DIR = "data/curated"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CLEAN_DIR, exist_ok=True)
os.makedirs(CURATED_DIR, exist_ok=True)


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    results = []

    for file in files:
        filename = file.filename
        file_path = os.path.join(RAW_DIR, filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        result = {
            "filename": filename,
            "raw_path": file_path,
            "status": "uploaded",
            "document_type": "not_processed",
            "extracted_data": {},
            "ocr_text_preview": "",
            "validation": {},
        }

        ext = os.path.splitext(filename)[1].lower()

        if ext in [".jpg", ".jpeg", ".png", ".pdf"]:
            try:
                text = extract_text(file_path)

                txt_filename = os.path.splitext(filename)[0] + ".txt"
                txt_path = os.path.join(CLEAN_DIR, txt_filename)
                with open(txt_path, "w", encoding="utf-8") as txt_file:
                    txt_file.write(text)

                doc_type = classify_document(text)
                extracted_data = extract_information(text)

                temp_doc = {
                    "filename": filename,
                    "document_type": doc_type,
                    "extracted_data": extracted_data,
                    "text": text,
                }

                validation_result = validate_document(temp_doc)

                json_filename = os.path.splitext(filename)[0] + ".json"
                json_path = os.path.join(CURATED_DIR, json_filename)

                curated_payload = {
                    "filename": filename,
                    "document_type": doc_type,
                    "text": text,
                    "extracted_data": extracted_data,
                    "validation": validation_result,
                }

                with open(json_path, "w", encoding="utf-8") as json_file:
                    json.dump(curated_payload, json_file, ensure_ascii=False, indent=2)

                result["status"] = "processed"
                result["document_type"] = doc_type
                result["extracted_data"] = extracted_data
                result["ocr_text_preview"] = text[:500]
                result["clean_path"] = txt_path
                result["curated_path"] = json_path
                result["validation"] = validation_result

            except Exception as e:
                result["status"] = f"processing_failed: {str(e)}"
        else:
            result["status"] = "uploaded_only"
            result["note"] = "Type de fichier non encore supporté."

        results.append(result)

    # Validation inter-documents si plusieurs fichiers
    cross_document_alerts = []
    if len(results) >= 2:
        processed_docs = [
            {
                "filename": r["filename"],
                "document_type": r.get("document_type"),
                "extracted_data": r.get("extracted_data", {}),
            }
            for r in results
            if r.get("status") == "processed"
        ]

        for i in range(len(processed_docs)):
            for j in range(i + 1, len(processed_docs)):
                alerts = check_inconsistencies(processed_docs[i], processed_docs[j])
                if alerts:
                    cross_document_alerts.append({
                        "doc1": processed_docs[i]["filename"],
                        "doc2": processed_docs[j]["filename"],
                        "alerts": alerts
                    })

    return {
        "results": results,
        "cross_document_alerts": cross_document_alerts
    }