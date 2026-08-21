import requests

headers = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

for url in [
    'https://trouverunlogement.lescrous.fr/api/fr/locations/search?q=toulouse',
    'https://trouverunlogement.lescrous.fr/api/fr/search/locations?q=toulouse',
    'https://trouverunlogement.lescrous.fr/api/fr/search/location?q=toulouse',
    'https://trouverunlogement.lescrous.fr/api/fr/zones?q=toulouse'
]:
    print("Trying:", url)
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(r.status_code)
        if r.status_code == 200:
            print(r.text[:500])
    except Exception as e:
        print(e)
