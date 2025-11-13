# Backend Python — FastAPI

Ce projet est un backend Python basé sur FastAPI, exécuté localement avec Uvicorn.
Il expose une API disponible en local via l’interface interactive Swagger.

---
 
## 🚀 Fonctionnalités

- API REST FastAPI
- Documentation automatique Swagger et Redoc
- Serveur local via Uvicorn
- Variables d’environnement isolées via un environnement virtuel

---

## 📦 Prérequis

- **Python 3.10+**
- **pip**


## 🔧 Installation
### 1. Cloner le projet
### 2. Créer et activer l’environnement virtuel

Sous Windows PowerShell :

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```


## ▶️ Lancer le serveur backend

```bash
uvicorn test:app --host 0.0.0.0 --port 8000 --reload
```

Le backend sera disponible sur :

Swagger UI 👉 http://127.0.0.1:8000/docs


## 🔐 Variables d’environnement

Si tu utilises des clés API, crée un fichier .env (qui NE doit pas être versionné) :

```bash
SECRET_KEY=xxxxxxxxxxxx
AZURE_API_KEY=xxxxxxxxxxxx
```

Et charge-le dans ton code via :

```bash
from dotenv import load_dotenv
load_dotenv()
```
