import unicodedata

def normalize(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower()

print(normalize("Agglomération Niçoise et Cagnes/Mer"))
print(normalize("Orléans"))
