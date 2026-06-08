import os
import json
import urllib.request
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

def test_pinnacle_source():
    if not BETSAPI_KEY:
        print("Erro: BETSAPI_KEY não encontrada.")
        return

    event_id = "11089991"
    sources_to_test = ["73", "3", "pinnacle", "ps3838", "bet365"]
    
    url_upcoming = f"https://api.betsapi.com/v2/events/upcoming?token={BETSAPI_KEY}&sport_id=1&league_id=33207"
    try:
        req = urllib.request.Request(url_upcoming, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("success") == 1:
                events = data.get("results", [])
                for ev in events:
                    ev_id = ev.get("id")
                    print(f"Testing event {ev_id} for pinnacle...")
                    url = f"https://api.betsapi.com/v2/event/odds?token={BETSAPI_KEY}&event_id={ev_id}&source=pinnacle"
                    try:
                        req2 = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req2) as res2:
                            data2 = json.loads(res2.read().decode('utf-8'))
                            if data2.get("success") == 1:
                                print(f"Event {ev_id} HAS pinnacle!")
                            else:
                                print(f"Event {ev_id} NO pinnacle (error: {data2.get('error')})")
                    except Exception as e:
                         pass
    except Exception as e:
         print(e)

if __name__ == "__main__":
    test_pinnacle_source()
