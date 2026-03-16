from fastapi import APIRouter, UploadFile, File
import os

router = APIRouter()

UPLOAD_DIR = "data/bronze"

os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    
    saved_files = []

    for file in files:
        path = os.path.join(UPLOAD_DIR, file.filename)

        with open(path, "wb") as f:
            f.write(await file.read())

        saved_files.append(file.filename)

    return {"uploaded": saved_files}