import os
import json

# Utiliser le volume persistant Docker s'il existe, sinon le dossier courant
DATA_DIR = "/app/data" if os.path.isdir("/app/data") else "."

CACHE_FILE = os.path.join(DATA_DIR, "crous_offres_connues.json")
CONFIG_FILE = os.path.join(DATA_DIR, "crous_config_surveillance.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "crous_sessions.json")
CREDENTIALS_FILE = os.path.join(DATA_DIR, "crous_credentials.json")
VILLES_FILE = "villes_crous.json" # Fichier statique, reste dans le dossier source

def charger_json(filepath, default):
    """Charge des données depuis un fichier JSON s'il existe"""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur chargement {filepath}: {e}")
    return default

def sauvegarder_json(filepath, data):
    """Sauvegarde des données dans un fichier JSON"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde {filepath}: {e}")
