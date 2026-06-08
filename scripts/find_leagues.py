import os
import json
import urllib.request
import urllib.parse
import urllib.error

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    key, val = line.strip().split("=", 1)
                    os.environ[key] = val.strip("'\"")

load_env()
BETSAPI_KEY = os.getenv("BETSAPI_KEY")

def search_league_by_name(name):
    base_url = "https://api.betsapi.com/v1/league"
    url = f"{base_url}?token={BETSAPI_KEY}&sport_id=1&name={urllib.parse.quote(name)}"
    # BetsAPI uses "search" instead of "name"? The docs say CC (country code) and maybe "search" ? Let's use v1/league?search=
    # Actually, often it's "name" or "search". Let's try both or just search. Wait, looking at common BetsAPI, it's typically /v1/league?token=xxx&sport_id=1&search=...
    # Let me try `search` param. Wait, actually /v1/league?sport_id=1&token=xxx&search=xxx
    # Let's do page=1
    
    url = f"{base_url}?token={BETSAPI_KEY}&sport_id=1&page=1"
    # Actually, fetching all leagues is paginated. Maybe I just fetch 10 pages and filter?
    pass

def full_league_search():
    if not BETSAPI_KEY:
        print("Erro: BETSAPI_KEY não encontrada.")
        return

    base_url = "https://api.betsapi.com/v1/league"
    keywords = ["world cup", "mls", "brazil serie a", "major league", "world cup 2026", "fifa"]
    
    found_leagues = set()
    print(f"Varrendo endpoint /v1/league completo usando urllib...")
    
    # Varre as primeiras 50 páginas de ligas (ou até acabar) para encontrar as corretas.
    # Ligas mais famosas geralmente estão nas primeiras páginas se ordenadas por relevância,
    # mas a API BetsAPI pode ter milhares.
    # Vou usar o parametro de busca textual em vez de percorrer paginas as cegas.
    pass

def search_api(query):
    base_url = "https://api.betsapi.com/v1/league"
    url = f"{base_url}?token={BETSAPI_KEY}&sport_id=1"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            for res in data.get("results", []):
                name = res.get("name", "").lower()
                if "world cup" in name or "mls" in name or "brazil" in name or "serie a" in name:
                    print(f"ID: {res['id']} | Nome: {res['name']}")
    except Exception as e:
        pass

def fetch_top_leagues():
    print("Minerando banco de ligas principal...")
    base_url = "https://api.betsapi.com/v1/league"
    keywords = ["friendlies", "international friendlies", "amistosos"]
    found = set()
    
    for page in range(1, 50):
        url = f"{base_url}?token={BETSAPI_KEY}&sport_id=1&page={page}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    break
                data = json.loads(response.read().decode('utf-8'))
                results = data.get("results", [])
                if not results:
                    break
                
                for res in results:
                    name = res.get("name", "")
                    name_lower = name.lower()
                    if any(kw in name_lower for kw in keywords):
                        found.add((res['id'], name))
        except Exception as e:
            pass

    print("\n--- Ligas Encontradas (Database Principal) ---")
    for l_id, l_name in sorted(list(found), key=lambda x: x[1]):
        print(f"ID: {l_id} | Nome: {l_name}")

if __name__ == "__main__":
    fetch_top_leagues()
