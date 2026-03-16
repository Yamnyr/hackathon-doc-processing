import os
import random
import numpy as np
import cv2
from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import cm
from PIL import Image, ImageDraw, ImageFont
from pymongo import MongoClient

# Configuration
OUTPUT_DIR = "dataset/generator/generated"
os.makedirs(OUTPUT_DIR, exist_ok=True)
fake = Faker("fr_FR")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/hackathon")
DB_NAME = "hackathon"
COLLECTION_NAME = "companies"

def get_companies():
    """Fetches companies from MongoDB."""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        coll = db[COLLECTION_NAME]
        companies = list(coll.find())
        if not companies:
            print("Warning: No companies found in MongoDB. Using Faker instead.")
        return companies
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return []

def add_noise(image):
    """Adds various types of noise to simulate real-world scans."""
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]

    # Rotation
    angle = random.uniform(-1.5, 1.5)
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    # Blur
    if random.random() > 0.5:
        k = random.choice([3, 5])
        img = cv2.GaussianBlur(img, (k, k), 0)

    # Lighting
    alpha = random.uniform(0.7, 1.3)
    beta = random.randint(-40, 40)
    img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

    # Grain
    if random.random() > 0.7:
        noise = np.random.randint(0, 50, (h, w, 3), dtype='uint8')
        img = cv2.add(img, noise)

    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

class RealisticDocumentGenerator:
    def __init__(self, output_dir, companies):
        self.output_dir = output_dir
        self.companies = companies
        self.width, self.height = A4

    def _get_random_company(self):
        if self.companies:
            return random.choice(self.companies)
        return {
            "name": fake.company(),
            "siren": fake.siren(),
            "address": fake.address()
        }

    def _draw_header(self, c, title, company_info):
        c.setFillColor(colors.HexColor("#2C3E50"))
        c.rect(0, self.height - 3*cm, self.width, 3*cm, fill=1)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(1*cm, self.height - 2*cm, title)
        
        c.setFont("Helvetica", 10)
        c.drawRightString(self.width - 1*cm, self.height - 1.5*cm, company_info.get("name", ""))
        addr = company_info.get("address", fake.address()).replace("\n", " ")
        c.drawRightString(self.width - 1*cm, self.height - 2.0*cm, addr)
        c.drawRightString(self.width - 1*cm, self.height - 2.5*cm, f"SIRET: {company_info.get('siren', '')}00012")

    def _draw_footer(self, c, text):
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(colors.grey)
        c.drawCentredString(self.width / 2, 1*cm, text)

    def generate_invoice_or_quote(self, i, doc_type="FACTURE", noisy=False, has_error=False):
        error_type = None
        if has_error:
            error_type = random.choice(["WRONG_MATH", "WRONG_SIRET", "MISSING_FIELD"])

        comp = self._get_random_company()
        sender = {
            "name": comp.get("name"),
            "address": comp.get("address", fake.address()),
            "siren": comp.get("siren")
        }
        
        client_comp = self._get_random_company()
        client = {
            "name": client_comp.get("name"),
            "address": client_comp.get("address", fake.address())
        }
        
        doc_no = f"{doc_type[:3]}-{fake.year()}-{i:04d}"
        if error_type == "MISSING_FIELD":
            doc_no = "" # Error: missing doc number

        date = fake.date()
        
        items = [["Description", "Qté", "Prix Unit.", "Total"]]
        total_ht = 0
        for _ in range(random.randint(3, 5)):
            qty = random.randint(1, 10)
            pu = random.randint(50, 500)
            line_total = qty * pu
            total_ht += line_total
            items.append([fake.catch_phrase()[:30], str(qty), f"{pu} €", f"{line_total} €"])
        
        tva = total_ht * 0.20
        total_ttc = total_ht + tva

        if error_type == "WRONG_MATH":
            total_ttc = total_ht + (tva * 1.5) # Error: invalid calc

        items.append(["", "", "Total HT", f"{total_ht} €"])
        items.append(["", "", "TVA (20%)", f"{tva:.2f} €"])
        items.append(["", "", "TOTAL TTC", f"{total_ttc:.2f} €"])

        prefix = "erroneous_" if has_error else ""
        filename = os.path.join(self.output_dir, f"{prefix}{doc_type.lower()}_{i}.pdf")
        
        c = canvas.Canvas(filename, pagesize=A4)
        
        if error_type == "WRONG_SIRET":
            sender["siren"] = "000000000" # Error: wrong siren

        self._draw_header(c, doc_type, sender)
        
        # Info
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*cm, self.height - 4*cm, f"N° DOCUMENT : {doc_no}")
        c.drawString(1*cm, self.height - 4.5*cm, f"DATE : {date}")
        
        # Recipient
        c.rect(self.width - 9*cm, self.height - 6.5*cm, 8*cm, 2.5*cm)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(self.width - 8.5*cm, self.height - 4.5*cm, "DESTINATAIRE :")
        c.setFont("Helvetica", 10)
        y_text = self.height - 5.0*cm
        for line in (client["name"] + "\n" + client["address"]).split('\n')[:3]:
            c.drawString(self.width - 8.5*cm, y_text, line)
            y_text -= 0.5*cm

        # Table
        table = Table(items, colWidths=[10*cm, 2*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#34495E")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -4), 1, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        w_t, h_t = table.wrap(self.width, self.height)
        table.drawOn(c, 1*cm, self.height - 8*cm - h_t)
        
        self._draw_footer(c, f"{sender['name']} - SIRET: {sender['siren']}00012 - Erreur: {error_type if has_error else 'None'}")
        c.save()

        if noisy:
             # Basic img for noise
             img = self._draw_img_mock(title=doc_type, sender=sender, client=client, items=items, error=error_type)
             img = add_noise(img)
             img.save(os.path.join(self.output_dir, f"{prefix}{doc_type.lower()}_{i}_noisy.jpg"), quality=40)

    def _draw_img_mock(self, title, sender, client, items, error=None):
        w, h = 1240, 1754
        img = Image.new('RGB', (w, h), (255, 255, 255))
        d = ImageDraw.Draw(img)
        try:
            f_title = ImageFont.truetype("arialbd.ttf", 60)
            f_reg = ImageFont.truetype("arial.ttf", 30)
        except:
            f_title = ImageFont.load_default()
            f_reg = ImageFont.load_default()

        d.rectangle([0, 0, w, 180], fill=(44, 62, 80))
        d.text((60, 50), title, fill=(255, 255, 255), font=f_title)
        
        y = 250
        d.text((60, y), f"DE: {sender['name']}", fill=(0,0,0), font=f_reg)
        d.text((60, y+40), f"SIRET: {sender['siren']}", fill=(0,0,0), font=f_reg)
        d.text((700, y), f"À: {client['name']}", fill=(0,0,0), font=f_reg)
        
        y = 600
        for row in items:
            d.text((60, y), " | ".join(row), fill=(0,0,0), font=f_reg)
            y += 60
            
        if error:
            d.text((60, h-100), f"DEBUG_ERROR_TYPE: {error}", fill=(200, 0, 0), font=f_reg)

        return img

    def generate_official_doc(self, i, doc_type="KBIS", noisy=False, has_error=False):
        comp = self._get_random_company()
        prefix = "erroneous_" if has_error else ""
        filename = os.path.join(self.output_dir, f"{prefix}{doc_type.lower()}_{i}.pdf")
        
        c = canvas.Canvas(filename, pagesize=A4)
        
        # Republic Header
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(self.width/2, self.height - 1*cm, "RÉPUBLIQUE FRANÇAISE")
        c.drawCentredString(self.width/2, self.height - 1.4*cm, "Liberté • Égalité • Fraternité")
        
        title = f"EXTRAIT {doc_type}"
        if doc_type == "RIB": title = "RELEVÉ D'IDENTITÉ BANCAIRE"
        
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(self.width/2, self.height - 3*cm, title)
        
        siren = comp.get('siren')
        if has_error and random.random() > 0.5:
            siren = "999999999" # Corrupted SIREN

        y = self.height - 5*cm
        fields = [
            ("Dénomination", comp.get('name')),
            ("SIREN", siren),
            ("Catégorie", comp.get('categorie')),
            ("Activité", comp.get('activite')),
            ("Date création", comp.get('date_creation'))
        ]
        
        for label, val in fields:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2*cm, y, f"{label}:")
            c.setFont("Helvetica", 10)
            c.drawString(7*cm, y, str(val))
            y -= 1*cm
            c.line(2*cm, y + 0.5*cm, self.width - 2*cm, y + 0.5*cm)

        c.save()
        
        if noisy:
            # Simplified noisy version
            img = Image.new('RGB', (1240, 1754), (255, 255, 255))
            d = ImageDraw.Draw(img)
            d.text((100, 100), f"{title} - {comp.get('name')}", fill=(0,0,0))
            img = add_noise(img)
            img.save(os.path.join(self.output_dir, f"{prefix}{doc_type.lower()}_{i}_noisy.jpg"), quality=30)

if __name__ == "__main__":
    companies = get_companies()
    gen = RealisticDocumentGenerator(OUTPUT_DIR, companies)
    
    doc_types = ["FACTURE", "DEVIS", "KBIS", "SIRET", "VIGILANCE", "RIB"]
    
    print(f"Génération de documents basés sur MongoDB dans {OUTPUT_DIR}...")
    
    for i in range(5):
        print(f"Lot {i+1}/5...")
        for dt in doc_types:
            # 1 normal clean
            # 1 normal noisy
            # 1 erroneous clean
            # 1 erroneous noisy
            
            if dt in ["FACTURE", "DEVIS"]:
                gen.generate_invoice_or_quote(i, dt, noisy=False, has_error=False)
                gen.generate_invoice_or_quote(i, dt, noisy=True, has_error=False)
                gen.generate_invoice_or_quote(i, dt, noisy=False, has_error=True)
                gen.generate_invoice_or_quote(i, dt, noisy=True, has_error=True)
            else:
                gen.generate_official_doc(i, dt, noisy=False, has_error=False)
                gen.generate_official_doc(i, dt, noisy=True, has_error=False)
                gen.generate_official_doc(i, dt, noisy=False, has_error=True)
                gen.generate_official_doc(i, dt, noisy=True, has_error=True)

    print("\nTerminé ! Dataset réaliste généré.")