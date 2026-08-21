import json
import re

with open('villes_original.json', 'r') as f:
    villes = json.load(f)

clean_villes = set()

for v in villes:
    v = v.replace("Agglomération Niçoise", "Nice")
    v = v.replace("Cagnes/Mer", "Cagnes-sur-Mer")
    v = v.replace("Lille-Villeneuve d'Ascq", "Lille et Villeneuve d'Ascq")
    v = v.replace("Lyon - Villeurbanne et Saint-Priest", "Lyon et Villeurbanne et Saint-Priest")
    v = v.replace("Versailles - St-quentin", "Versailles et Saint-Quentin-en-Yvelines")
    v = v.replace("Savoie - ", "")
    v = v.replace("Drome - ", "")
    v = v.replace("Isere - ", "")
    v = v.replace("Haute Savoie - ", "")
    v = v.replace("Toulon et Alentours", "Toulon")
    v = v.replace("Roubaix - Tourcoing", "Roubaix et Tourcoing")
    v = v.replace("Longuenesse - Saint Omer", "Longuenesse et Saint-Omer")
    v = v.replace("Lens-Liévin", "Lens et Liévin")
    
    parts = re.split(r'\s+et\s+|/', v)
    for p in parts:
        p = p.strip()
        p = re.sub(r'(?i)\s+(centre|sud|nord|est|ouest|intra-muros).*', '', p).strip()
        p = re.sub(r'\s+-.*', '', p).strip()
        
        if "Marseille" in p: p = "Marseille"
        if "Nancy" in p: p = "Nancy"
        if "Metz" in p: p = "Metz"
        if "Cayenne" in p: p = "Cayenne"
        if "Pointe-à-Pitre" in p: p = "Pointe-à-Pitre"
        if "Saint-claude" in p.lower(): p = "Saint-Claude"
        if "Campus" in p or "Pôle" in p or "Site" in p or "Service" in p or "agglomération" in p:
            continue
            
        if p:
            clean_villes.add(p)

clean_list = sorted(list(clean_villes))

with open('villes_crous.json', 'w') as f:
    json.dump(clean_list, f, indent=2, ensure_ascii=False)
