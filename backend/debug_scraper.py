import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Acessando Premier League...")
        await page.goto("https://www.oddsagora.com.br/football/england/campeonato-ingles/", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        # Tirar print
        await page.screenshot(path="debug_oddsagora.png")
        print("Screenshot salvo em debug_oddsagora.png")
        
        # Listar links
        links = await page.eval_on_selector_all('a', 'elements => elements.map(e => e.href)')
        print(f"Total links encontrados: {len(links)}")
        for l in links[:20]:
            print(f"  {l}")
            
        await browser.close()

asyncio.run(debug())
