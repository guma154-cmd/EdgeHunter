import asyncio
import aiohttp

async def test():
    headers = {
        "X-API-Key": "CmX2KcMrRmaAjNgj",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    url = "https://guest.api.arcadia.pinnacle.com/0.1/matchups?sportIds=33"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers) as r:
            print(f"Status: {r.status}")
            if r.status == 200:
                data = await r.json()
                print(f"Count: {len(data)}")
            else:
                print(await r.text())

if __name__ == "__main__":
    asyncio.run(test())
