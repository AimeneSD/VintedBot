import json
import re

with open('villes_crous.json', 'r') as f:
    villes = json.load(f)

clean_villes = set()
for v in villes:
    v_clean = v
    if "Niçoise" in v: v_clean = "Nice"
    if "Lille" in v: v_clean = "Lille"
    if "Grenoble" in v: v_clean = "Grenoble"
    if "Lyon" in v: v_clean = "Lyon"
    if "Marseille" in v: v_clean = "Marseille"
    if "Nancy" in v: v_clean = "Nancy"
    if "Paris" in v: v_clean = "Paris"
    if "Toulon" in v: v_clean = "Toulon"
    if "Savoie" in v: v_clean = "Chambéry" if "Chambéry" in v else "Le Bourget-du-Lac"
    if "Drome" in v: v_clean = "Valence"
    if "Metz" in v: v_clean = "Metz"
    if "Cayenne" in v: v_clean = "Cayenne"
    if "Pointe-à-Pitre" in v: v_clean = "Pointe-à-Pitre"
    if "Saint-claude" in v.lower(): v_clean = "Saint-Claude"
    
    # Generic regex
    v_clean = re.sub(r'(?i)\s+(centre|sud|nord|est|ouest|intra-muros|-).*', '', v_clean).strip()
    
    if v_clean:
        clean_villes.add(v_clean)

# Common cities
clean_villes.update(["Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Nantes", "Montpellier", "Strasbourg", "Bordeaux", "Lille", "Rennes"])

clean_list = sorted(list(clean_villes))

with open('villes_crous.json', 'w') as f:
    json.dump(clean_list, f, indent=2, ensure_ascii=False)
