import os
import json

CACHE_FILE = "offres_connues.json"
CONFIG_FILE = "config_surveillance.json"
SESSIONS_FILE = "sessions.json"
VILLES_FILE = "villes_crous.json"
CREDENTIALS_FILE = "credentials.json"

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
