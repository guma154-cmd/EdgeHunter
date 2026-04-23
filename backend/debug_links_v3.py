import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.oddsagora.com.br/football/england/campeonato-ingles/", wait_until="networkidle")
        try: await page.get_by_role("button", name="Aceito").click()
        except: pass
        await page.wait_for_timeout(5000)
        
        # Encontrar links que tenham texto de times
        links = await page.eval_on_selector_all('a', '''elements => elements.map(e => ({
            href: e.href,
            text: e.innerText,
            html: e.outerHTML
        }))''')
        
        for l in links:
            if "-" in l['text'] and len(l['text']) > 5:
                print(f"POSSIBLE MATCH: {l['href']} | TEXT: {l['text']}")
            # Tentar achar pelo HTML
            if "campeonato-ingles" in l['href'] and len(l['href'].split('/')) > 5:
                 if any(team in l['text'].lower() for team in ["liverpool", "chelsea", "arsenal", "city", "united"]):
                     print(f"FOUND FAMOUS TEAM: {l['href']} | TEXT: {l['text']}")

        await browser.close()

asyncio.run(debug())
