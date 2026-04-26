import asyncio
import aiohttp

async def find_leagues():
    headers = {
        "X-API-Key": "CmX2KcMrRmaAjNgj",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    # Tentar endpoint alternativo para listar ligas
    url = "https://guest.api.arcadia.pinnacle.com/0.1/leagues?sportId=33"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            print(f"Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                for l in data:
                    if l.get('hasOfferings'):
                        print(f"ID: {l['id']} | Name: {l['name']}")
            else:
                print(await resp.text())

if __name__ == "__main__":
    asyncio.run(find_leagues())
