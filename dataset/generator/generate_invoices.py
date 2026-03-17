import os
import random
import numpy as np
import cv2
from datetime import datetime
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

    # Rotation (skew)
    angle = random.uniform(-1.2, 1.2)
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

    # Blur
    if random.random() > 0.4:
        k = random.choice([3, 5])
        img = cv2.GaussianBlur(img, (k, k), 0)

    # Lighting
    alpha = random.uniform(0.85, 1.15)
    beta = random.randint(-20, 20)
    img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

    # Grain
    if random.random() > 0.7:
        noise = np.random.randint(0, 25, (h, w, 3), dtype='uint8')
        img = cv2.add(img, noise)

    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

class DynamicProfessionalGenerator:
    def __init__(self, output_dir, companies):
        self.output_dir = output_dir
        self.companies = companies
        self.width, self.height = A4
        # Professional color palettes
        self.palettes = [
            {"primary": "#2C3E50", "secondary": "#34495E", "accent": "#3498DB"}, # Midnight Blue
            {"primary": "#1A5276", "secondary": "#21618C", "accent": "#5DADE2"}, # Ocean
            {"primary": "#1E8449", "secondary": "#239B56", "accent": "#82E0AA"}, # Emerald
            {"primary": "#7D3C98", "secondary": "#8E44AD", "accent": "#BB8FCE"}, # Amethyst
            {"primary": "#212F3D", "secondary": "#2E4053", "accent": "#F1C40F"}  # Dark Charcoal + Gold
        ]

    def _get_random_company(self):
        if self.companies:
            return random.choice(self.companies)
        return {"name": fake.company(), "siren": fake.siren(), "address": fake.address()}

    def _apply_layout_style(self, c, title, sender, palette):
        """Randomly Choose between multiple layout structures (Modern, Classic, Lateral)."""
        style = random.choice(["MODERN", "CLASSIC", "MINIMALIST"])
        
        if style == "MODERN":
            # Top solid bar
            c.setFillColor(colors.HexColor(palette['primary']))
            c.rect(0, self.height - 3.5*cm, self.width, 3.5*cm, fill=1)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 28)
            c.drawString(1*cm, self.height - 2*cm, title)
            c.setFont("Helvetica", 10)
            c.drawRightString(self.width - 1*cm, self.height - 1.2*cm, sender['name'])
            c.drawRightString(self.width - 1*cm, self.height - 1.7*cm, sender['address'].replace('\n', ' ')[:60])
            c.drawRightString(self.width - 1*cm, self.height - 2.2*cm, f"SIRET: {sender['siren']}00012")
        
        elif style == "CLASSIC":
            # Just text, no bars, sender on top left
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(1*cm, self.height - 1.5*cm, sender['name'])
            c.setFont("Helvetica", 10)
            c.drawString(1*cm, self.height - 2*cm, sender['address'].replace('\n', ' ')[:60])
            c.drawString(1*cm, self.height - 2.4*cm, f"SIRET: {sender['siren']}00012")
            
            c.setFont("Helvetica-Bold", 24)
            c.drawCentredString(self.width/2, self.height - 4*cm, title)
            c.line(1*cm, self.height - 4.5*cm, self.width - 1*cm, self.height - 4.5*cm)

        else: # MINIMALIST
            # Thin accent line on the left
            c.setFillColor(colors.HexColor(palette['accent']))
            c.rect(0, 0, 0.5*cm, self.height, fill=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica-Bold", 30)
            c.drawString(1.5*cm, self.height - 3*cm, title)
            c.setFont("Helvetica", 11)
            c.drawRightString(self.width - 1*cm, self.height - 2*cm, sender['name'])
            c.drawRightString(self.width - 1*cm, self.height - 2.5*cm, f"SIRET: {sender['siren']}00012")

        return style

    def generate_invoice_or_quote(self, i, doc_type="FACTURE", noisy=False, has_error=False):
        palette = random.choice(self.palettes)
        error_type = random.choice(["WRONG_MATH", "WRONG_SIRET", "MISSING_FIELD", "EXPIRED"]) if has_error else None

        comp = self._get_random_company()
        sender = {"name": comp.get("name"), "address": comp.get("address", fake.address()), "siren": comp.get("siren")}
        client_comp = self._get_random_company()
        client = {"name": client_comp.get("name"), "address": client_comp.get("address", fake.address())}
        
        doc_no = f"{doc_type[:3]}-{datetime.now().year}-{i:04d}" if error_type != "MISSING_FIELD" else ""
        date_val = fake.date_between(start_date='-5y', end_date='-2y') if error_type == "EXPIRED" else datetime.now()
        date_str = date_val.strftime("%d/%m/%Y") if hasattr(date_val, 'strftime') else date_val

        # Items
        items = [["Description", "Qté", "PU", "Total"]]
        total_ht = 0
        for _ in range(random.randint(3, 10)):
            q, p = random.randint(1, 5), random.randint(20, 1000)
            total_ht += (q * p)
            items.append([fake.catch_phrase()[:35], str(q), f"{p}€", f"{q*p}€"])
        
        tva = total_ht * 0.20
        total_ttc = total_ht + tva
        if error_type == "WRONG_MATH": total_ttc += 150.50

        items.append(["", "", "Total HT", f"{total_ht}€"])
        items.append(["", "", "TVA (20%)", f"{tva:.2f}€"])
        items.append(["", "", "TOTAL TTC", f"{total_ttc:.2f}€"])

        prefix = "erroneous_" if has_error else ""
        filename = os.path.join(self.output_dir, f"{prefix}{doc_type.lower()}_{i}.pdf")
        
        c = canvas.Canvas(filename, pagesize=A4)
        if error_type == "WRONG_SIRET": sender["siren"] = "000000000"

        style_name = self._apply_layout_style(c, doc_type, sender, palette)
        
        # Details Placement based on style
        c.setFillColor(colors.black)
        y = self.height - 6*cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1*cm, y, f"N° : {doc_no}")
        c.drawString(1*cm, y - 0.5*cm, f"DATE : {date_str}")

        # Recipient
        c.rect(self.width - 8.5*cm, y - 2*cm, 7.5*cm, 2.5*cm)
        c.drawString(self.width - 8*cm, y - 0.2*cm, "CLIENT :")
        c.setFont("Helvetica", 10)
        y_c = y - 0.8*cm
        for line in (client['name'] + '\n' + client['address']).split('\n')[:3]:
            c.drawString(self.width - 8*cm, y_c, line[:45])
            y_c -= 0.5*cm

        # Table
        table = Table(items, colWidths=[9.5*cm, 1.5*cm, 3.5*cm, 3.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(palette['secondary'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -4), 0.5, colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (2, -3), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        
        w_t, h_t = table.wrap(self.width, self.height)
        table.drawOn(c, 1*cm, y - 4*cm - h_t)
        
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(self.width/2, 1.5*cm, f"{sender['name']} - Capital {random.randint(1000, 50000)}€ - SIRET {sender['siren']}00012")
        c.save()

        if noisy:
            img = self._draw_img_dynamic(doc_type, sender, client, items, doc_no, date_str, palette, style_name)
            img = add_noise(img)
            img.save(os.path.join(self.output_dir, f"{prefix}{doc_type.lower()}_{i}_noisy.jpg"), quality=35)

    def _draw_img_dynamic(self, title, sender, client, items, doc_no, date, palette, style):
        w, h = 1240, 1754
        img = Image.new('RGB', (w, h), (255, 255, 255))
        d = ImageDraw.Draw(img)
        try:
            f_title = ImageFont.truetype("arialbd.ttf", 60)
            f_bold = ImageFont.truetype("arialbd.ttf", 35)
            f_reg = ImageFont.truetype("arial.ttf", 28)
        except:
            f_title, f_bold, f_reg = [ImageFont.load_default()]*3

        # Header Styles in Image
        if style == "MODERN":
            d.rectangle([0, 0, w, 220], fill=palette['primary'])
            d.text((60, 60), title, fill=(255, 255, 255), font=f_title)
            d.text((w-600, 50), sender['name'], fill=(255,255,255), font=f_bold)
        elif style == "CLASSIC":
            d.text((60, 60), sender['name'], fill=(0,0,0), font=f_bold)
            d.text((w/2 - 100, 180), title, fill=(0,0,0), font=f_title)
            d.line([60, 260, w-60, 260], fill=(0,0,0), width=3)
        else: # MINIMALIST
            d.rectangle([0, 0, 40, h], fill=palette['accent'])
            d.text((80, 100), title, fill=(0,0,0), font=f_title)

        y = 350
        d.text((80, y), f"REF: {doc_no}", fill=(0,0,0), font=f_bold)
        d.text((80, y+50), f"DATE: {date}", fill=(0,0,0), font=f_reg)

        # Dest Box
        d.rectangle([w-550, y, w-60, y+200], outline=(0,0,0), width=2)
        d.text((w-530, y+20), client['name'], fill=(0,0,0), font=f_bold)
        d.text((w-530, y+70), client['address'].replace('\n', ' ')[:40], fill=(0,0,0), font=f_reg)

        # Dynamic table grid
        y_t = 650
        d.rectangle([80, y_t, w-80, y_t+60], fill=palette['secondary'])
        d.text((100, y_t+10), "DESCRIPTION", fill=(255,255,255), font=f_reg)
        d.text((w-200, y_t+10), "TOTAL", fill=(255,255,255), font=f_reg)
        
        y_r = y_t + 60
        for row in items[1:-3]:
            d.line([80, y_r, w-80, y_r], fill=(200,200,200), width=1)
            d.text((100, y_r+15), row[0], fill=(0,0,0), font=f_reg)
            d.text((w-200, y_r+15), row[3], fill=(0,0,0), font=f_reg)
            y_r += 65
            
        y_r += 40
        for row in items[-3:]:
            d.text((w-400, y_r), f"{row[2]}: {row[3]}", fill=(0,0,0), font=f_bold)
            y_r += 60

        return img

    def generate_official_doc(self, i, doc_type="KBIS", noisy=False, has_error=False):
        comp = self._get_random_company()
        error_type = random.choice(["WRONG_DATA", "EXPIRED"]) if has_error else None
        prefix = "erroneous_" if has_error else ""
        filename = os.path.join(self.output_dir, f"{prefix}{doc_type.lower()}_{i}.pdf")
        
        date_v = fake.date_between(start_date='-4y', end_date='-1y') if error_type == "EXPIRED" else datetime.now()
        date_s = date_v.strftime("%d/%m/%Y") if hasattr(date_v, 'strftime') else date_v

        c = canvas.Canvas(filename, pagesize=A4)
        # Randomize official border or simplified look
        if random.random() > 0.5:
            c.setStrokeColor(colors.lightgrey)
            c.rect(1*cm, 1*cm, self.width-2*cm, self.height-2*cm)

        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(self.width/2, self.height - 1.5*cm, "RÉPUBLIQUE FRANÇAISE")
        
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(self.width/2, self.height - 3.5*cm, f"DOCUMENT OFFICIEL : {doc_type}")
        
        y = self.height - 6*cm
        fields = [
            ("Dénomination", comp.get('name')),
            ("Numéro SIREN", "999999999" if error_type == "WRONG_DATA" else comp.get('siren')),
            ("Délivré le", date_s),
            ("Code APE", comp.get('activite')),
            ("Forme Juridique", random.choice(["SAS", "SARL", "EURL"]))
        ]
        
        for label, val in fields:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2*cm, y, f"{label}:")
            c.setFont("Helvetica", 11)
            c.drawString(9*cm, y, str(val))
            y -= 1.2*cm
            c.setDash(1, 3)
            c.line(2*cm, y+0.8*cm, self.width-2*cm, y+0.8*cm)
            c.setDash()

        c.save()
        if noisy:
            img = self._draw_img_official_dynamic(doc_type, fields)
            img = add_noise(img)
            img.save(os.path.join(self.output_dir, f"{prefix}{doc_type.lower()}_{i}_noisy.jpg"), quality=30)

    def _draw_img_official_dynamic(self, title, fields):
        w, h = 1240, 1754
        img = Image.new('RGB', (w, h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            f_title = ImageFont.truetype("arialbd.ttf", 50)
            f_bold = ImageFont.truetype("arialbd.ttf", 35)
            f_reg = ImageFont.truetype("arial.ttf", 30)
        except:
            f_title, f_bold, f_reg = [ImageFont.load_default()]*3

        draw.text((w/2 - 200, 100), "RÉPUBLIQUE FRANÇAISE", fill=(0,0,0), font=f_bold)
        draw.text((w/2 - 250, 220), title, fill=(0,0,0), font=f_title)
        
        y = 450
        for l, v in fields:
            draw.text((150, y), f"{l}:", fill=(100,100,100), font=f_reg)
            draw.text((550, y), str(v), fill=(0,0,0), font=f_bold)
            y += 100
            draw.line([150, y-20, w-150, y-20], fill=(200,200,200), width=1)
        return img

if __name__ == "__main__":
    companies = get_companies()
    gen = DynamicProfessionalGenerator(OUTPUT_DIR, companies)
    doc_types = ["FACTURE", "DEVIS", "KBIS", "SIRET", "VIGILANCE", "RIB"]
    
    print(f"Génération de dataset DYNAMIQUE dans {OUTPUT_DIR}...")
    for i in range(5):
        print(f"Lot {i+1}/5...")
        for dt in doc_types:
            for error_flag in [False, True]:
                # Clean
                gen.generate_invoice_or_quote(i, dt, noisy=False, has_error=error_flag) if dt in ["FACTURE", "DEVIS"] else gen.generate_official_doc(i, dt, noisy=False, has_error=error_flag)
                # Noisy
                gen.generate_invoice_or_quote(i, dt, noisy=True, has_error=error_flag) if dt in ["FACTURE", "DEVIS"] else gen.generate_official_doc(i, dt, noisy=True, has_error=error_flag)

    print("\nDataset PRO et HÉTÉROGÈNE généré avec succès.")