import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Acessando Premier League...")
        await page.goto("https://www.oddsagora.com.br/football/england/campeonato-ingles/", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        
        # Clicar no Accept
        try:
            await page.click('button:has-text("I Accept")', timeout=5000)
            print("Cookies aceitos.")
        except:
            print("Botão I Accept não encontrado ou já aceito.")
            
        await page.wait_for_timeout(3000)
        
        # Tirar print depois de aceitar
        await page.screenshot(path="debug_oddsagora_post_cookies.png")
        
        # Listar links
        links = await page.eval_on_selector_all('a', 'elements => elements.map(e => e.href)')
        print(f"Total links: {len(links)}")
        
        # Filtrar links que contenham a estrutura de partida
        match_links = [l for l in links if "campeonato-ingles/" in l and len(l.split('/')) >= 7]
        for l in match_links[:10]:
            print(f"MATCH LINK: {l}")
            
        await browser.close()

asyncio.run(debug())
