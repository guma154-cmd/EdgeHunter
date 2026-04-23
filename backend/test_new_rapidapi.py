import http.client

conn = http.client.HTTPSConnection("free-api-live-football-data.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "b34e28fce5msh1204c7f0b3cc58bp1c0fc8jsncdd52ecbe149",
    'x-rapidapi-host': "free-api-live-football-data.p.rapidapi.com",
    'Content-Type': "application/json"
}

try:
    conn.request("GET", "/football-players-search?search=m", headers=headers)
    res = conn.getresponse()
    data = res.read()
    print(data.decode("utf-8"))
except Exception as e:
    print(f"Erro ao testar API: {e}")
