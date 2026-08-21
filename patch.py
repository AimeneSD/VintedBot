import os

critere_file = "critere.md"
with open(critere_file, "r", encoding="utf-8") as f:
    critere_content = f.read()

header_addition = """
.venv/bin/python -c '
import os

# 1. Update critere.md
critere_file = "critere.md"
with open(critere_file, "r", encoding="utf-8") as f:
    critere_content = f.read()

header_addition = """
cat critere.md! RÈGLE ABSOLUE SUR LES MANETTES !!!
Tu dois IMPÉRATIVEMENT REJETER ("recommandation": "À FUIR", "is_semantic_match": false) TOUTES les manettes non officielles (marques tierces, compatibles, Nacon, Scuf, PDP, génériques, fausses manettes sans marque).
JE NE VEUX QUE DES MANETTES OFFICIELLES (Sony PlayStation, Microsoft Xbox, Nintendo).
Si le titre, la description ou la marque indiquent que ce n'\''est pas une manette officielle, c'\''est un rejet immédiat, peu importe le prix ou la panne.
"""
if "RÈGLE ABSOLUE SUR LES MANETTES" not in critere_content:
    critere_content = header_addition + "\n" + critere_content
    with open(critere_file, "w", encoding="utf-8") as f:
        f.write(critere_content)


# 2. Update utils/gemini.py
gemini_file = "utils/gemini.py"
with open(gemini_file, "r", encoding="utf-8") as f:
    gemini_content = f.read()

old_vision_prompt = """Vois-tu des vices cachés graves non mentionnés qui rendraient l'objet inutilisable ou non réparable (ex: carte mère à nue sans coque, produit cassé en deux, oxydation majeure) ?"""
new_vision_prompt = """Vois-tu des vices cachés graves non mentionnés qui rendraient l'\''objet inutilisable ou non réparable (ex: carte mère à nue sans coque, produit cassé en deux, oxydation majeure) ?
ATTENTION PARTICULIÈRE POUR LES MANETTES : Vérifie VISUELLEMENT que la manette est bien une manette OFFICIELLE (présence du logo PlayStation sur le bouton PS, logo Xbox, logo Nintendo). Si l'\''image montre une manette générique, tierce, ou une contrefaçon évidente sans le logo officiel de la marque, c'\''est un vice rédhibitoire."""

if old_vision_prompt in gemini_content:
    gemini_content = gemini_content.replace(old_vision_prompt, new_vision_prompt)
    with open(gemini_file, "w", encoding="utf-8") as f:
        f.write(gemini_content)

print("Patch successful!")
'! RÈGLE ABSOLUE SUR LES MANETTES !!!
Tu dois IMPÉRATIVEMENT REJETER ("recommandation": "À FUIR", "is_semantic_match": false) TOUTES les manettes non officielles (marques tierces, compatibles, Nacon, Scuf, PDP, génériques, fausses manettes sans marque).
JE NE VEUX QUE DES MANETTES OFFICIELLES (Sony PlayStation, Microsoft Xbox, Nintendo).
Si le titre, la description ou la marque indiquent que ce n'est pas une manette officielle, c'est un rejet immédiat, peu importe le prix ou la panne.
"""
if "RÈGLE ABSOLUE SUR LES MANETTES" not in critere_content:
    critere_content = header_addition + "\n" + critere_content
    with open(critere_file, "w", encoding="utf-8") as f:
        f.write(critere_content)

gemini_file = "utils/gemini.py"
with open(gemini_file, "r", encoding="utf-8") as f:
    gemini_content = f.read()

old_vision_prompt = """Vois-tu des vices cachés graves non mentionnés qui rendraient l'objet inutilisable ou non réparable (ex: carte mère à nue sans coque, produit cassé en deux, oxydation majeure) ?"""
new_vision_prompt = """Vois-tu des vices cachés graves non mentionnés qui rendraient l'objet inutilisable ou non réparable (ex: carte mère à nue sans coque, produit cassé en deux, oxydation majeure) ?
ATTENTION PARTICULIÈRE POUR LES MANETTES : Vérifie VISUELLEMENT que la manette est bien une manette OFFICIELLE (présence du logo PlayStation sur le bouton PS, logo Xbox, logo Nintendo). Si l'image montre une manette générique, tierce, ou une contrefaçon évidente sans le logo officiel de la marque, c'est un vice rédhibitoire."""

if old_vision_prompt in gemini_content:
    gemini_content = gemini_content.replace(old_vision_prompt, new_vision_prompt)
    with open(gemini_file, "w", encoding="utf-8") as f:
        f.write(gemini_content)

print("Patch successful!")
