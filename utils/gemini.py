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
    
    prompt = f"""
Titre de l'annonce : {titre}
Prix demandé : {prix}
Description :
{description}

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown autour.
Structure attendue :
{{
  "is_semantic_match": true ou false,
  "confidence_score": entier entre 0 et 100,
  "recommandation": "🟢 FONCE", "🟠 RISQUÉ", ou "🔴 À FUIR",
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
