# Hackathon – Traitement automatique de documents administratifs

Projet réalisé dans le cadre du hackathon IPSSI.

Objectif : développer une **plateforme capable d’analyser automatiquement des documents administratifs** (factures, devis, attestations…) afin de :

* classifier les documents
* extraire les informations clés
* détecter des incohérences ou fraudes
* alimenter des outils métiers (CRM / conformité)

---
# 🚀 Fonctionnalités principales

### 1️ Upload multi-documents
Interface permettant de charger plusieurs documents administratifs.

### 2️ Classification automatique
Détection automatique du type de document :
* Factures
* Devis
* Attestations SIRET / KBIS / Vigilance URSSAF
* RIB

### 3️ OCR & Extraction d'informations
* Extraction du texte à partir des documents PDF ou images.
* Extraction de données structurées : SIREN, SIRET, montants, dates, noms d'entreprises.

### 4️ Génération de Dataset Synthétique & Réel
* **Données réelles** : Intégration de la base SIRENE (INSEE) avec 20 entreprises stockées en MongoDB.
* **Templates Pro** : Génération de documents réalistes (PDF) avec calculs de TVA, en-têtes officiels et pieds de page.
* **Robustesse** : Simulation de scans bruités (rotation, flou, bruit numérique) et insertion d'erreurs métier (calculs faux, SIRET invalides) pour tester la détection de fraude.

### 5️ Data Lake (Architecture Medallion)
* **Bronze** : Documents bruts.
* **Silver** : Texte extrait par OCR.
* **Gold** : Données structurées prêtes pour l'analyse.

---

# 🏗️ Architecture Technique

### Pipeline Global
1. **Source** : Upload client ou Dataset généré via `StockUniteLegale_utf8.csv`.
2. **Stockage** : Persistence des documents et données métiers dans **MongoDB**.
3. **Traitement** : Pipeline OCR (Tesseract) → Extraction (NLP/Regex) → Validation.
4. **Dashboard** : Visualisation des alertes et données exploitables.

### Structure des dossiers
```
hackathon-doc-processing/
├── backend/                # FastAPI / Logique métier
├── frontend/               # Streamlit Dashboard
├── data/                   # Data Lake (Bronze/Silver/Gold)
├── dataset/
│   └── generator/          # Scripts de génération de documents
│       ├── generate_invoices.py
│       ├── import_companies.py
│       └── generated/      # Fichiers PDF/JPG produits
├── docker-compose.yml      # Orchestration (Backend, Mongo, Frontend)
└── requirements.txt        # Dépendances Python
```

---

# 🛠️ Installation & Démarrage

## 1️ Via Docker (Recommandé)
Le projet utilise Docker pour orchestrer le backend, le frontend et la base de données MongoDB.

```bash
docker-compose up --build
```

## 2️ Installation Manuelle

### Dépendances Système
* **Tesseract OCR** : Doit être installé sur votre machine.

### Environnement Python
Avec conda :
```bash
conda create -n hackathon python=3.10
conda activate hackathon
```
ou avec venv :
```bash
source venv/bin/activate  # (ou venv\Scripts\activate sur Windows)
```
```bash
# Installation
pip install -r requirements.txt
```
### Initialisation du Dataset
Pour générer les données à partir de la base SIRENE (nécessite le fichier `StockUniteLegale_utf8.csv` à la racine) :

```bash
# 1. Lancer MongoDB
docker-compose up -d mongodb

# 2. Importer les entreprises de la base SIRENE
python dataset/generator/import_companies.py

# 3. Générer le dataset (PDF/JPG)
python dataset/generator/generate_invoices.py
```

### Lancement des services

Lancer le backend (FastAPI) :
```bash
uvicorn backend.app.main:app --reload
```

Lancer le frontend (Streamlit) :
```bash
streamlit run frontend/app.py
```

---

# 🧠 Technologies utilisées

* **Backend** : FastAPI, Python, MongoDB
* **OCR** : Tesseract, OpenCV, Pillow, ReportLab (Génération PDF)
* **Data** : Faker (Données synthétiques), Base SIRENE (Données réelles)
* **Frontend** : Streamlit
* **DevOps** : Docker, Docker-Compose

---

# 🎯 Objectif Final
Fournir une solution de bout en bout pour automatiser les contrôles de conformité KYC/KYB en détectant instantanément les documents falsifiés ou les erreurs de saisie administrative.
