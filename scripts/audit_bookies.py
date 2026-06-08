import os
import requests
from dotenv import load_dotenv

def run():
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    api_key = os.getenv("BETSAPI_KEY")
    if not api_key:
        print("API key missing!")
        return
    
    event_id = "11089991"
    
    print(f"Analisando evento {event_id}...")
    
    v2_url = f"https://api.betsapi.com/v2/event/odds/summary?token={api_key}&event_id={event_id}"
    try:
        r2 = requests.get(v2_url, timeout=10)
        data2 = r2.json()
        if data2.get("success") == 1 and data2.get("results"):
            print("\n=== Casas encontradas na v2/event/odds/summary ===")
            results = data2["results"]
            if isinstance(results, dict):
                for k in results.keys():
                    print(f" - {k}")
            elif isinstance(results, list):
                for item in results:
                    print(f" - {item}")
            else:
                print(f"Formato desconhecido: {type(results)}")
            return
        else:
            print(f"\nv2/event/odds/summary falhou ou retornou vazio: {data2}")
    except Exception as e:
        print(f"Erro na v2: {e}")

    v3_url = f"https://api.betsapi.com/v3/events/odds?token={api_key}&event_id={event_id}"
    try:
        r3 = requests.get(v3_url, timeout=10)
        data3 = r3.json()
        if data3.get("success") == 1 and data3.get("results"):
            print("\n=== Casas encontradas na v3/events/odds ===")
            results = data3["results"]
            if isinstance(results, dict):
                for k in results.keys():
                    print(f" - {k}")
            elif isinstance(results, list) and len(results) > 0 and isinstance(results[0], dict):
                bookies = set()
                for item in results:
                    if 'source' in item:
                        bookies.add(item['source'])
                for b in bookies:
                    print(f" - {b}")
                if not bookies:
                    # just print keys of first item
                    print(f"Resultados brutos (chaves): {list(results[0].keys())}")
            else:
                print(f"Resultados brutos: {results}")
        else:
            print(f"\nv3/events/odds falhou ou retornou vazio: {data3}")
    except Exception as e:
        print(f"Erro na v3: {e}")

if __name__ == "__main__":
    run()
