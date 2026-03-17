import os
import cv2
import pytesseract
import numpy as np
import pypdfium2 as pdfium


def _preprocess_image(img: np.ndarray) -> np.ndarray:
    if img is None:
        raise ValueError("Image vide ou illisible.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return thresh


def extract_text_from_image(image_path: str) -> str:
    img = cv2.imread(image_path)

    if img is None:
        raise ValueError(f"Impossible de lire le fichier image : {image_path}")

    processed = _preprocess_image(img)
    text = pytesseract.image_to_string(processed)
    return text.strip()


def extract_text_from_pdf(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        raise ValueError(f"PDF introuvable : {pdf_path}")

    pdf = pdfium.PdfDocument(pdf_path)
    all_text = []

    for i in range(len(pdf)):
        page = pdf[i]
        bitmap = page.render(scale=2)
        pil_image = bitmap.to_pil()
        img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

        processed = _preprocess_image(img)
        page_text = pytesseract.image_to_string(processed)
        all_text.append(page_text.strip())

    return "\n".join(all_text).strip()


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".jpg", ".jpeg", ".png"]:
        return extract_text_from_image(file_path)

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)

    raise ValueError(f"Type de fichier non supporté pour OCR : {ext}")