import utils.database as db
import os
import json
import time
import asyncio
from google import genai
from google.genai import types
from google.genai.errors import APIError

_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY non définie dans le .env")
        _client = genai.Client(api_key=api_key)
    return _client

def get_system_prompt():
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "critere.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Tu es un expert en réparation électronique. Évalue la rentabilité de l'annonce."

async def analyze_item_async(item_data):
    return await asyncio.to_thread(analyze_item, item_data)

def analyze_item(item_data, max_retries=3):
    try:
        client = get_client()
    except ValueError as e:
        print(f"[Gemini] {e}")
        return None
        
    system_prompt = get_system_prompt()
    
    fallback_models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-1.5-flash",
    ]
    
    titre = item_data.get("title", "Sans titre")
    description = item_data.get("description", "Sans description")
    prix = item_data.get("price", "Inconnu")
    etat = item_data.get("condition", "Inconnu")
    
    # --- CONTEXTE MARCHÉ DEPUIS SQLITE ---
    market_context = "\n\n--- INFO MARCHÉ (Base de données locale) ---\n"
    
    # Historique Vinted
    clean_title = ' '.join([w for w in titre.lower().replace('-', ' ').split() if len(w) > 2])
    vinted_avg = None
    if clean_title:
        # Essayer avec les 2 premiers mots importants
        keywords = ' '.join(clean_title.split()[:2])
        vinted_avg = db.get_average_vinted_price(keywords)
    
    if vinted_avg:
        market_context += f"- Prix moyen Vinted pour '{keywords}': {vinted_avg['avg_price']} EUR (basé sur {vinted_avg['count']} annonces).\n"
    else:
        market_context += "- Prix moyen Vinted: Inconnu.\n"
        
    # Composants Aliexpress
    components = db.get_all_component_prices()
    if components:
        market_context += "- Prix moyens des pièces de rechange (Aliexpress) :\n"
        for comp, p in components.items():
            market_context += f"  * {comp.title()}: {p} EUR\n"
    market_context += "----------------------------------------------\n"
    
    # -------------------------------------
    
    prompt = f"""
Titre de l'annonce : {titre}
État : {etat}
Prix demandé : {prix}
Description :
{description}

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown autour.
Structure attendue :
{{
  "is_semantic_match": true ou false (true SI c'est une console/manette/smartphone, false SEULEMENT si c'est un vêtement, jeu vidéo physique, peluche, accessoire inutile, etc. La rentabilité ne doit pas influencer ce champ),
  "confidence_score": entier entre 0 et 100,
  "recommandation": "FONCE", "RISQUE", ou "A FUIR",
  "category_detected": "Ex: Console, Smartphone...",
  "financial_estimation": {{
    "estimated_resale_value_euros": entier,
    "estimated_repair_cost_euros": entier,
    "estimated_net_profit_euros": entier
  }},
  "red_flags": ["..."],
  "green_flags": ["..."],
  "repairs_needed": ["..."],
  "translated_description": "..."
}}
"""
    
    config = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
        system_instruction=system_prompt
    )

    for model in fallback_models:
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                
                time.sleep(4) # Rate Limit protection
                
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_text = "\n".join(lines)
                
                try:
                    data = json.loads(raw_text)
                    
                    # Sauvegarder les nouvelles pièces estimées
                    new_pieces = data.get("nouvelles_pieces_estimees", {})
                    if isinstance(new_pieces, dict):
                        for piece, price in new_pieces.items():
                            try:
                                db.add_component_price(piece, float(price), "IA-JIT")
                                print(f"[Gemini] Nouvelle pièce sauvegardée : {piece} à {price}€")
                            except Exception as db_err:
                                print(f"[Gemini] Erreur sauvegarde pièce : {db_err}")
                                
                    return data
                except json.JSONDecodeError as e:
                    print(f"[Gemini] Erreur de parsing JSON : {e}")
                    return None
                    
            except APIError as e:
                if e.code == 429:
                    print(f"[Gemini] Quota épuisé pour {model}. Passage au modèle suivant...")
                    break
                else:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        print(f"[Gemini] Échec avec {model} : {e}")
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    print(f"[Gemini] Erreur inattendue : {e}")
                    
    print("[Gemini] Tous les modèles de fallback ont échoué.")
    return None


async def verify_image_async(image_bytes: bytes, previous_analysis: dict) -> dict:
    """Deuxième passe : analyse visuelle de l'image pour confirmer/infirmer le texte."""
    if not image_bytes:
        return previous_analysis
        
    prompt = f"""Tu es un expert en réparation d'électronique et consoles.
Voici l'analyse textuelle préliminaire d'une annonce Vinted :
{json.dumps(previous_analysis, indent=2, ensure_ascii=False)}

TA TÂCHE :
Examine attentivement l'image jointe à cette annonce. Confirme-t-elle l'analyse textuelle ?
Vois-tu des vices cachés graves non mentionnés qui rendraient l'objet inutilisable ou non réparable (ex: carte mère à nue sans coque, produit cassé en deux, oxydation majeure) ?

Si l'image révèle un vice rédhibitoire (comme une coque complètement manquante sur une manette), TU DOIS forcer :
"recommandation": "À FUIR"
"is_semantic_match": false

Sinon, conserve ou affine la recommandation, et ajoute tes observations visuelles dans "red_flags" ou "green_flags".
Réponds UNIQUEMENT avec un objet JSON valide reprenant exactement la même structure que l'analyse préliminaire, mais mis à jour avec tes observations visuelles.
"""
    try:
        response = await get_client().aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')
            ]
        )
        response_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(response_text)
    except Exception as e:
        print(f"[Gemini] Erreur lors de l'analyse visuelle : {e}")
        return previous_analysis
