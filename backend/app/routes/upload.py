from fastapi import APIRouter, UploadFile, File

from backend.app.services.datalake import (
    create_document_entry,
    generate_batch_id,
    generate_document_id,
    init_datalake,
    save_to_bronze,
)

router = APIRouter()

# Ensure Data Lake folders exist when the router is loaded
init_datalake()


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    """
    Accept one or more documents, assign them a shared batch_id, persist each
    raw file to the Bronze layer, and record metadata in MongoDB.
    """
    batch_id = generate_batch_id()
    saved = []

    for file in files:
        document_id = generate_document_id()
        file_bytes = await file.read()

        metadata = save_to_bronze(document_id, file.filename, file_bytes, batch_id)
        create_document_entry(metadata)

        saved.append(
            {
                "document_id": document_id,
                "filename":    file.filename,
                "bronze_path": metadata["file_path"],
                "batch_id":    batch_id,
                "status":      "raw",
            }
        )

    return {"batch_id": batch_id, "uploaded": saved}
