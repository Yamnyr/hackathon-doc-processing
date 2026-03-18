import os
import random
import numpy as np
import cv2
import uuid
from datetime import datetime, timedelta
from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from PIL import Image, ImageDraw, ImageFont
from pymongo import MongoClient

# Configuration
OUTPUT_DIR = "dataset/generator/generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)
fake = Faker("fr_FR")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/hackathon")
DB_NAME = "hackathon"
COLLECTION_NAME = "companies"

def get_companies():
    """Fetches companies from MongoDB or uses defaults."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
        db = client[DB_NAME]
        coll = db[COLLECTION_NAME]
        companies = list(coll.find())
        return companies
    except:
        return []

def add_photo_effect(image):
    """Adds light noise to simulate a handheld phone photo without breaking OCR."""
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]

    # 1. Very Light Perspective
    if random.random() > 0.5:
        src_pts = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        offset = random.randint(5, 15)
        dst_pts = np.float32([
            [random.randint(0, offset), random.randint(0, offset)],
            [w - random.randint(0, offset), random.randint(0, offset)],
            [random.randint(0, offset), h - random.randint(0, offset)],
            [w - random.randint(0, offset), h - random.randint(0, offset)]
        ])
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        img = cv2.warpPerspective(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    # 2. Light Blur
    if random.random() > 0.7:
        img = cv2.GaussianBlur(img, (3, 3), 0)

    # 3. Light Grain/Noise
    noise = np.random.randint(0, 5, (h, w, 3), dtype='uint8')
    img = cv2.add(img, noise)

    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

class DatasetGenerator:
    def __init__(self, output_dir, companies):
        self.output_dir = output_dir
        self.companies = companies
        self.width, self.height = A4
        self.img_size = (1500, 2000)

    def _get_company(self):
        if self.companies:
            c = random.choice(self.companies)
            return {
                "name": c.get("name", fake.company()),
                "siren": c.get("siren", fake.siren()),
                "siret": c.get("siret", c.get("siren", fake.siren()) + "00012"),
                "address": c.get("address", fake.address().replace("\n", ", "))
            }
        return {"name": fake.company(), "siren": fake.siren(), "address": fake.address()}

    def _generate_amounts(self):
        ht = round(random.uniform(500, 2000), 2)
        tva = round(ht * 0.20, 2)
        ttc = round(ht + tva, 2)
        return ht, tva, ttc

    def generate_batch(self, batch_id, has_anomaly=False):
        company = self._get_company()
        siret = company['siret']
        print(f"Generating batch for: {company['name']} ({siret})")
        docs = ["FACTURE", "DEVIS", "VIGILANCE"]
        
        anomaly_type = "CLEAN"
        if has_anomaly:
            # Simple, distinct anomaly types
            anomaly_type = random.choice(["MATH_ERROR", "SIRET_MISSING", "EXPIRED_DOC", "SIRET_DB_MISSING"])
        
        for doc_type in docs:
            current_siret = siret
            current_date = datetime.now()
            ht, tva, ttc = self._generate_amounts()
            
            # Application of anomaly
            if has_anomaly:
                if anomaly_type == "MATH_ERROR" and doc_type in ["FACTURE", "DEVIS"]:
                    ttc += 500.0 # Clear math inconsistency
                elif anomaly_type == "SIRET_MISSING":
                    current_siret = "" 
                elif anomaly_type == "EXPIRED_DOC" and doc_type == "VIGILANCE":
                    current_date = datetime.now() - timedelta(days=500)
                elif anomaly_type == "SIRET_DB_MISSING":
                    current_siret = "99988877700012" # Not in DB

            effective_label = anomaly_type if not (anomaly_type == "EXPIRED_DOC" and doc_type != "VIGILANCE") else "CLEAN"
            prefix = f"batch_{batch_id}_{effective_label}_{doc_type.lower()}"
            
            self._create_pdf(os.path.join(self.output_dir, f"{prefix}.pdf"), doc_type, company, current_siret, current_date, ht, tva, ttc)
            self._create_photo(os.path.join(self.output_dir, f"{prefix}_photo.jpg"), doc_type, company, current_siret, current_date, ht, tva, ttc)

    def _create_pdf(self, path, doc_type, company, siret, date, ht, tva, ttc):
        c = canvas.Canvas(path, pagesize=A4)
        h = self.height
        w = self.width

        c.setFont("Helvetica-Bold", 40)
        c.drawCentredString(w/2, h-3*cm, doc_type)
        
        c.setFont("Helvetica", 24)
        y = h - 6*cm
        c.drawString(2*cm, y, f"COMPANY: {company['name']}")
        c.drawString(2*cm, y-1.5*cm, f"SIRET: {siret}")
        c.drawString(2*cm, y-3*cm, f"DATE: {date.strftime('%d/%m/%Y')}")
        
        if doc_type in ["FACTURE", "DEVIS"]:
            y -= 8*cm
            c.setFont("Helvetica-Bold", 30)
            c.drawString(2*cm, y, f"TOTAL HT: {ht} EUR")
            c.drawString(2*cm, y-1.5*cm, f"TVA (20%): {tva} EUR")
            c.drawString(2*cm, y-3*cm, f"TOTAL TTC: {ttc} EUR")
        else:
            y -= 8*cm
            c.setFont("Helvetica", 24)
            c.drawString(2*cm, y, "ATTESTATION DE VIGILANCE URSSAF")
            c.drawString(2*cm, y-1.5*cm, f"VALIDE AU: {date.strftime('%d/%m/%Y')}")
            
        c.save()

    def _create_photo(self, path, doc_type, company, siret, date, ht, tva, ttc):
        img = Image.new('RGB', self.img_size, color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font_title = ImageFont.truetype("arial.ttf", 100)
            font_text = ImageFont.truetype("arial.ttf", 60)
        except:
            font_title = font_text = ImageFont.load_default()

        draw.text((self.img_size[0]//2 - 200, 100), doc_type, fill=(0, 0, 0), font=font_title)
        y = 400
        draw.text((100, y), f"COMPANY: {company['name']}", fill=(0,0,0), font=font_text)
        draw.text((100, y+100), f"SIRET: {siret}", fill=(0,0,0), font=font_text)
        draw.text((100, y+200), f"DATE: {date.strftime('%d/%m/%Y')}", fill=(0,0,0), font=font_text)
        
        if doc_type in ["FACTURE", "DEVIS"]:
            draw.text((100, y+500), f"TOTAL HT: {ht} EUR", fill=(0,0,0), font=font_text)
            draw.text((100, y+600), f"TVA (20%): {tva} EUR", fill=(0,0,0), font=font_text)
            draw.text((100, y+700), f"TOTAL TTC: {ttc} EUR", fill=(0,0,0), font=font_text)
        else:
            draw.text((100, y+500), "ATTESTATION URSSAF VALIDE", fill=(0,0,0), font=font_text)

        photo = add_photo_effect(img)
        photo.save(path, "JPEG", quality=95)

if __name__ == "__main__":
    companies = get_companies()
    gen = DatasetGenerator(OUTPUT_DIR, companies)
    
    # Cleanup
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith((".pdf", ".jpg")):
            os.remove(os.path.join(OUTPUT_DIR, f))
            
    print(f"Génération Epurée (Ebauche 3.0) dans {OUTPUT_DIR}...")
    for i in range(2):
        gen.generate_batch(f"clean_{i}", has_anomaly=False)
    for i in range(5):
        gen.generate_batch(f"error_{i}", has_anomaly=True)
    print("\nDataset ultra-simple (Labels clairs) généré.")