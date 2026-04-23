import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Acessando Premier League...")
        await page.goto("https://www.oddsagora.com.br/football/england/campeonato-ingles/", wait_until="networkidle")
        
        try:
            await page.get_by_role("button", name="Aceito").click()
            print("Cookies aceitos.")
        except: pass
            
        await page.wait_for_timeout(5000)
        
        # Tirar print
        await page.screenshot(path="debug_final.png", full_page=True)
        
        # Pegar TODOS os links e seus textos
        elements = await page.query_selector_all('a')
        print(f"Total links: {len(elements)}")
        for el in elements:
            href = await el.get_attribute('href')
            text = await el.inner_text()
            if href and "campeonato-ingles" in href and len(href.split('/')) > 5:
                print(f"LINK: {href} | TEXTO: {text}")
            
        await browser.close()

asyncio.run(debug())
