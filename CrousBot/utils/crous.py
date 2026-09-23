import math
import requests
import os
import json
import base64
import hashlib
import re
from bs4 import BeautifulSoup

RAYON_DEFAULT_KM = 25

cookies_base = {
    'tool.47.hasUserReadRules': 'true',
}

headers = {
    'Accept': 'application/ld+json, application/json',
    'Accept-Language': 'fr-FR,fr;q=0.5',
    'Content-Type': 'application/json',
    'Origin': 'https://trouverunlogement.lescrous.fr',
    'Referer': 'https://trouverunlogement.lescrous.fr/',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
}



def obtenir_coordonnees(nom_ville):
    """Convertit un nom de ville en coordonnées GPS et Bounding Box grâce à Nominatim"""
    nom_ville_clean = re.sub(r'(?i)\s+(centre|sud|nord|est|ouest|intra-muros|-).*', '', nom_ville).strip()
    if not nom_ville_clean:
        nom_ville_clean = nom_ville
    url = f"https://nominatim.openstreetmap.org/search?q={nom_ville_clean}&format=json&limit=1"
    headers_osm = {"User-Agent": "CrousBot/1.0"}
    try:
        r = requests.get(url, headers=headers_osm, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                nom_officiel = data[0]['display_name'].split(',')[0]
                boundingbox = data[0].get('boundingbox')
                if boundingbox:
                    min_lat, max_lat, min_lon, max_lon = map(float, boundingbox)
                    bbox = [
                        {'lon': min_lon, 'lat': max_lat},
                        {'lon': max_lon, 'lat': min_lat}
                    ]
                else:
                    bbox = None
                return lat, lon, nom_officiel, bbox
    except Exception as e:
        print(f"Erreur Géocodage : {e}")
    return None, None, None, None

def chercher_crous(lat, lon, rayon_km=RAYON_DEFAULT_KM, bbox=None, phpsessid=None):
    """Effectue la requête au CROUS dans une Bounding Box exacte ou un périmètre"""
    if bbox and rayon_km == RAYON_DEFAULT_KM:
        location = bbox
    else:
        delta_lat = rayon_km / 111.0
        rad_lat = math.radians(lat)
        delta_lon = rayon_km / (111.0 * max(math.cos(rad_lat), 0.1))
        location = [
            {'lon': lon - delta_lon, 'lat': lat + delta_lat},
            {'lon': lon + delta_lon, 'lat': lat - delta_lat},
        ]

    json_data = {
        'idTool': 47,
        'need_aggregation': True,
        'page': 1,
        'pageSize': 48,
        'sector': None,
        'occupationModes': [],
        'location': location,
        'residence': None,
        'precision': 6,
        'equipment': [],
        'price': {'max': 10000000},
        'area': {'min': 0},
        'adaptedPmr': False,
        'toolMechanism': 'residual',
    }
    
    req_cookies = cookies_base.copy()
    if phpsessid:
        req_cookies['PHPSESSID'] = phpsessid

    try:
        response = requests.post(
            'https://trouverunlogement.lescrous.fr/api/fr/search/47',
            cookies=req_cookies,
            headers=headers,
            json=json_data,
            proxies=get_proxies(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get('results', {}).get('items', [])
    except Exception as e:
        print(f"Erreur API CROUS : {e}")
    return []


def get_proxies():
    """Retourne le proxy SOCKS5 (Wireproxy) pour utiliser l'IP résidentielle Free"""
    return {
        "http": "socks5h://127.0.0.1:1080",
        "https": "socks5h://127.0.0.1:1080"
    }

def verifier_session(phpsessid):
    """Vérifie si la session (PHPSESSID) est toujours valide."""
    if not phpsessid:
        return False
        
    req_cookies = {'PHPSESSID': phpsessid}
    try:
        response = requests.get(
            'https://trouverunlogement.lescrous.fr/api/fr/user',
            cookies=req_cookies,
            headers=headers,
            proxies=get_proxies(),
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data is not None:
                return True
            else:
                return False
        elif response.status_code in [401, 403]:
            return False
        else:
            print(f"Erreur vérification session : Code HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Erreur vérification session (Exception) : {e}")
        return None

def solve_altcha(challenge_json_str):
    challenge_data = json.loads(challenge_json_str)
    salt = challenge_data['salt']
    challenge = challenge_data['challenge']
    max_number = challenge_data.get('maxNumber', 100000)
    algorithm = challenge_data.get('algorithm', 'SHA-256')

    for n in range(max_number + 1):
        text = salt + str(n)
        if algorithm == 'SHA-256':
            hash_hex = hashlib.sha256(text.encode('utf-8')).hexdigest()
        else:
            raise Exception("Unsupported algorithm")
        
        if hash_hex == challenge:
            payload = {
                "algorithm": algorithm,
                "challenge": challenge,
                "number": n,
                "salt": salt,
                "signature": challenge_data['signature']
            }
            return base64.b64encode(json.dumps(payload, separators=(',', ':')).encode('utf-8')).decode('utf-8')
    raise Exception("Altcha max number reached")

def renouveler_session_automatiquement(email, password):
    """Effectue tout le parcours OAuth2 + Altcha pour récupérer un PHPSESSID valide"""
    print(f"Tentative de connexion pour {email}...")
    
    for attempt in range(3):
        if attempt > 0:
            print(f"Nouvelle tentative de connexion ({attempt+1}/3)...")
            import time
            time.sleep(2)
            
        try:
            s = requests.Session()
            s.headers.update(headers)
            
            # 1. Obtenir les jetons initiaux
            r1 = s.get('https://trouverunlogement.lescrous.fr/mse/discovery/connect', allow_redirects=True, proxies=get_proxies(), timeout=15)
            soup1 = BeautifulSoup(r1.text, 'html.parser')
            form1 = soup1.find('form', {'name': 'login'})
            if not form1:
                print(f"Erreur: Formulaire Etape 1 introuvable. Code HTML partiel: {r1.text[:200]}")
                continue
                
            payload1 = {}
            for input_tag in form1.find_all('input'):
                name = input_tag.get('name')
                if name:
                    if name == 'login[app]':
                        if input_tag.get('value') == '0':
                            payload1[name] = '0'
                    else:
                        payload1[name] = input_tag.get('value', '')
                        
            # 2. Obtenir le formulaire de login avec Altcha
            r2 = s.post(r1.url, data=payload1, allow_redirects=True, proxies=get_proxies(), timeout=15)
            soup2 = BeautifulSoup(r2.text, 'html.parser')
            form2 = soup2.find('form', {'name': 'login'})
            
            if not form2:
                print("Erreur: Formulaire Etape 2 introuvable")
                continue
                
            payload2 = {}
            for input_tag in form2.find_all('input'):
                name = input_tag.get('name')
                if name and name not in ['login[login]', 'login[password]']:
                    payload2[name] = input_tag.get('value', '')
                    
            altcha_tag = soup2.find('altcha-widget')
            if altcha_tag:
                challenge_json = altcha_tag.get('challengejson')
                print("Résolution du défi Altcha PoW en cours...")
                payload2['login[altcha]'] = solve_altcha(challenge_json)
            
            payload2['login[login]'] = email
            payload2['login[password]'] = password
            
            # 3. Soumettre le login et suivre les redirections pour obtenir le PHPSESSID final
            r3 = s.post(r2.url, data=payload2, allow_redirects=True, proxies=get_proxies(), timeout=20)
            
            # 4. Effectuer un dernier appel sur le domaine trouverunlogement.lescrous.fr pour forcer l'enregistrement du cookie
            r4 = s.get('https://trouverunlogement.lescrous.fr/api/fr/user', proxies=get_proxies(), timeout=15)
            
            cookies = s.cookies.get_dict()
            phpsessid = cookies.get('PHPSESSID')
            
            # DEBUG PRINTS
            print(f"DEBUG: Après Step 3, URL finale = {r3.url}")
            print(f"DEBUG: Cookies récupérés = {cookies}")
            if phpsessid:
                is_valid = verifier_session(phpsessid)
                print(f"DEBUG: PHPSESSID récupéré ({phpsessid[:5]}...), verifier_session = {is_valid}")
                if is_valid:
                    print("Authentification réussie ! PHPSESSID récupéré.")
                    return phpsessid
                else:
                    print("DEBUG: PHPSESSID invalide selon l'API /user")
            else:
                print("DEBUG: Aucun PHPSESSID trouvé dans les cookies.")
                print(f"DEBUG: Code HTML partiel r3: {r3.text[:250]}")
                
            print("Echec de l'authentification (identifiants invalides ou bloqué).")
            # Ne retourne pas None tout de suite, on laisse la boucle réessayer si c'est un blocage
        except requests.exceptions.Timeout:
            print("Erreur : Timeout lors de la connexion. Le proxy ou le CROUS est très lent.")
        except requests.exceptions.RequestException as e:
            print(f"Erreur réseau : {e}")
            
    print("Toutes les tentatives de connexion ont échoué.")
    return None
