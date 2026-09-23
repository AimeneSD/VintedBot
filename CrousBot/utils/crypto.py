import os
from cryptography.fernet import Fernet

def get_cipher():
    key = os.getenv("CROUS_ENCRYPTION_KEY")
    if not key:
        print("[AVERTISSEMENT] CROUS_ENCRYPTION_KEY non définie dans les variables d'environnement.")
        return None
    try:
        return Fernet(key.encode('utf-8'))
    except ValueError:
        print("[ERREUR] La clé CROUS_ENCRYPTION_KEY est invalide (doit être une clé Fernet base64 url-safe).")
        return None

def chiffrer(texte: str) -> str:
    """Chiffre une chaîne de caractères en AES."""
    if not texte:
        return texte
        
    cipher = get_cipher()
    if cipher is None:
        # Si aucune clé, on renvoie le texte tel quel (pour ne pas bloquer complètement, mais c'est risqué)
        return texte
        
    return cipher.encrypt(texte.encode('utf-8')).decode('utf-8')

def dechiffrer(texte_chiffre: str) -> str:
    """Déchiffre une chaîne de caractères AES."""
    if not texte_chiffre:
        return texte_chiffre
        
    cipher = get_cipher()
    if cipher is None:
        return texte_chiffre
        
    try:
        return cipher.decrypt(texte_chiffre.encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"[Crypto] Erreur de déchiffrement: {e}")
        # Si ça plante (ex: texte pas chiffré ou clé modifiée), on retourne le texte tel quel au cas où
        # c'était de l'ancien texte en clair.
        return texte_chiffre
