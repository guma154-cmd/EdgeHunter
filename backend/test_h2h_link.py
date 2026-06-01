import pytest
pytest.importorskip("playwright")
import asyncio
from playwright.async_api import async_playwright

async def test_match():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.oddsagora.com.br/football/h2h/nottingham-UsushcZr/sunderland-WSzc94ws/#0AH7bYWj"
        print(f"Acessando {url}...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path="debug_match_page.png")
        
        content = await page.content()
        print(f"Tamanho do HTML: {len(content)}")
        if "pinnacle" in content.lower():
            print("Pinnacle encontrada!")
        if "betano" in content.lower():
            print("Betano encontrada!")
            
        await browser.close()

asyncio.run(test_match())
