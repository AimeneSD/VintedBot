import json

with open('villes_crous.json', 'r') as f:
    villes = json.load(f)

bad = ["Droit", "Technologies", "Artem", "Bridoux", "environs", "Haute Annecy", "Saint-claude", "Toulon ville", "Lettres"]
clean = [v for v in villes if v not in bad]
if "Annecy" not in clean: clean.append("Annecy")
clean.sort()

with open('villes_crous.json', 'w') as f:
    json.dump(clean, f, indent=2, ensure_ascii=False)
