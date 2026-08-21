import re

tests = [
    "Toulouse Centre - Ouest",
    "Toulouse Sud-Est",
    "Amiens centre",
    "Amiens nord",
    "Amiens sud",
    "Paris intra-muros",
    "Agglomération Niçoise et Cagnes/Mer",
    "Bourg-en-Bresse",
    "Cergy-Pontoise",
    "Châlons-en-Champagne",
    "Côte basque - Landes",
    "Pau - Pays de l'Adour"
]

for t in tests:
    clean = re.sub(r'(?i)\s+(centre|sud|nord|est|ouest|intra-muros|-).*', '', t).strip()
    print(f"'{t}' -> '{clean}'")
