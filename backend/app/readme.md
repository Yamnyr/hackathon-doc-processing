# 🚀 Hackathon – Traitement automatique de documents administratifs

Projet réalisé dans le cadre du hackathon IPSSI.

Objectif : développer une **plateforme capable d’analyser automatiquement des documents administratifs** (factures, devis, attestations…) afin de :

* classifier les documents
* extraire les informations clés
* détecter des incohérences ou fraudes
* alimenter des outils métiers (CRM / conformité)

---

# 🧠 Fonctionnalités principales

### 1️⃣ Upload multi-documents

Interface permettant de charger plusieurs documents administratifs.

### 2️⃣ Classification automatique

Détection automatique du type de document :

* facture
* devis
* attestation
* contrat

### 3️⃣ OCR (Optical Character Recognition)

Extraction du texte à partir des documents PDF ou images.

### 4️⃣ Extraction d’informations

Extraction automatique de :

* SIREN
* SIRET
* montants
* dates
* nom entreprise

### 5️⃣ Détection d’incohérences

Exemples :

* SIREN différent entre facture et attestation
* montant facture ≠ devis
* SIRET invalide

### 6️⃣ Data Lake

Architecture **Medallion** :

Bronze → documents bruts
Silver → texte OCR
Gold → données structurées

### 7️⃣ Dashboard / Frontend

Interface permettant de visualiser :

* les documents analysés
* les informations extraites
* les alertes de fraude

---

# 🏗 Architecture du projet

Pipeline global :

Upload documents
↓
Stockage Bronze (documents bruts)
↓
OCR extraction
↓
Classification document
↓
Extraction informations
↓
Détection incohérences
↓
Stockage Gold (données structurées)
↓
Dashboard / CRM

---

# 📂 Structure du projet

```
hackathon-doc-processing/

backend/
    app/
        main.py
        routes/
            upload.py
        pipeline/
            ocr.py
            classifier.py
            extractor.py
            validator.py
        services/
            storage.py
            database.py

frontend/
    app.py

data/
    bronze/
    silver/
    gold/

models/
notebooks/
tests/

requirements.txt
README.md
```

---

# ⚙️ Installation

## 1️⃣ Cloner le projet

```
git clone https://github.com/ORG/hackathon-doc-processing.git
cd hackathon-doc-processing
```

---

## 2️⃣ Créer un environnement Python

Avec conda :

```
conda create -n hackathon python=3.10
conda activate hackathon
```

ou avec venv :

```
python -m venv venv
source venv/bin/activate
```

Windows :

```
venv\Scripts\activate
```

---

## 3️⃣ Installer les dépendances

```
pip install -r requirements.txt
```

---

## 4️⃣ Lancer le backend

```
uvicorn backend.app.main:app --reload
```

API accessible :

```
http://127.0.0.1:8000
```

Documentation automatique :

```
http://127.0.0.1:8000/docs
```

---

## 5️⃣ Lancer le frontend

```
streamlit run frontend/app.py
```

---

# 👥 Organisation de l’équipe (6 personnes)

## 👨‍💻 Backend / API

Responsable :

* API FastAPI
* endpoints
* orchestration pipeline

Fichiers :

```
backend/app/main.py
backend/app/routes
```

---

## 👨‍💻 OCR / Traitement documents

Responsable :

* conversion PDF → image
* preprocessing
* extraction texte

Fichiers :

```
backend/app/pipeline/ocr.py
```

---

## 👨‍💻 Extraction d’informations

Responsable :

* extraction SIREN
* extraction montants
* extraction dates
* regex / NLP

Fichiers :

```
backend/app/pipeline/extractor.py
```

---

## 👨‍💻 Classification documents

Responsable :

* modèle classification
* facture / devis / attestation
* ML ou règles

Fichiers :

```
backend/app/pipeline/classifier.py
```

---

## 👨‍💻 Data / Stockage

Responsable :

* Data Lake
* stockage bronze/silver/gold
* base de données

Fichiers :

```
backend/app/services
data/
```

---

## 👨‍💻 Frontend / Dashboard

Responsable :

* interface upload
* visualisation résultats
* alertes fraude

Fichiers :

```
frontend/app.py
```

---

# 📅 Planning du hackathon

## Lundi

Architecture + setup projet

* repo GitHub
* structure projet
* distribution des tâches

---

## Mardi

Pipeline documents

* upload documents
* OCR extraction

---

## Mercredi

IA / NLP

* classification documents
* extraction informations

---

## Jeudi

Vérification + dashboard

* détection incohérences
* interface frontend

---

## Vendredi

Finalisation

* pipeline complet
* démo
* préparation pitch

---

# 🧪 Exemple d’incohérences détectées

SIREN différent entre documents

```
facture.siren != attestation.siren
```

Montant facture différent du devis

```
facture.montant > devis.montant
```

SIRET invalide

```
len(siret) != 14
```

---

# 🚀 Technologies utilisées

Backend

* FastAPI
* Python

OCR

* Tesseract
* OpenCV

NLP

* spaCy
* regex

Machine Learning

* scikit-learn

Frontend

* Streamlit

---

# 🎯 Objectif final

Une plateforme capable de :

* analyser automatiquement des documents administratifs
* extraire les informations importantes
* détecter des incohérences
* aider les entreprises à automatiser les contrôles documentaires

---
