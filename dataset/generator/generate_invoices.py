from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import random

fake = Faker("fr_FR")

OUTPUT_DIR = "data/raw/generated"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_invoice(i):

    filename = f"{OUTPUT_DIR}/invoice_{i}.pdf"

    c = canvas.Canvas(filename, pagesize=A4)

    company = fake.company()
    address = fake.address()
    date = fake.date()
    siret = fake.siret()
    amount = random.randint(100, 5000)

    c.drawString(100, 750, "FACTURE")
    c.drawString(100, 720, f"Entreprise : {company}")
    c.drawString(100, 700, f"Adresse : {address}")
    c.drawString(100, 680, f"SIRET : {siret}")
    c.drawString(100, 660, f"Date : {date}")
    c.drawString(100, 640, f"Montant TTC : {amount} €")

    c.save()


for i in range(50):
    generate_invoice(i)

print("Factures générées")