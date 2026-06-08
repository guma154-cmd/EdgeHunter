import asyncio
import aiohttp
import os
import sys
from datetime import datetime, timezone
import logging
from sqlalchemy import select, update, text
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import AsyncDatabase, ValueOpportunityLog

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BETSAPI_KEY = os.getenv("BETSAPI_KEY", "")
SOURCE = "PinnacleSports"

async def fetch_closing_line(session: aiohttp.ClientSession, event_id: str) -> dict:
    url = f"https://api.betsapi.com/v2/event/odds?token={BETSAPI_KEY}&event_id={event_id}&source={SOURCE}"
    try:
        async with session.get(url, timeout=10) as response:
            data = await response.json()
            if data.get("success") == 1:
                odds_history = data.get("results", {}).get("odds", {}).get("1_1", [])
                if odds_history:
                    closing_line = odds_history[-1]
                    return {
                        "home": float(closing_line.get("home_od", 0)),
                        "draw": float(closing_line.get("draw_od", 0)),
                        "away": float(closing_line.get("away_od", 0))
                    }
            else:
                logger.warning("Falha na API para event_id %s: %s", event_id, data.get("error"))
    except Exception as e:
        logger.error("Erro crítico de rede para event_id %s: %s", event_id, e)
    return {}

async def run_clv_extraction():
    db = AsyncDatabase()
    await db.init_db()

    query_sql = text("""
        SELECT id, event_id, selection 
        FROM value_opportunity_log 
        WHERE clv_updated_at IS NULL 
          AND match_details->>'time' IS NOT NULL
          AND (match_details->>'time')::bigint BETWEEN EXTRACT(EPOCH FROM NOW()) - 7200 AND EXTRACT(EPOCH FROM NOW()) + 900
    """)

    async with aiohttp.ClientSession() as http_session:
        while True:
            try:
                async with db.AsyncSessionLocal() as session:
                    result = await session.execute(query_sql)
                    rows = result.fetchall()
                    
                    if not rows:
                        logger.info("Nenhuma oportunidade aguardando CLV nesta janela.")
                    
                    # Agrupar oportunidades pelo event_id
                    events_map = {}
                    for row in rows:
                        ev_id = str(row.event_id)
                        if ev_id not in events_map:
                            events_map[ev_id] = []
                        events_map[ev_id].append(row)
                    
                    for event_id, event_rows in events_map.items():
                        logger.info("Buscando CLV para event_id: %s", event_id)
                        clv_data = await fetch_closing_line(http_session, event_id)
                        
                        if not clv_data:
                            logger.info("Nenhum dado de CLV encontrado para event_id: %s", event_id)
                            await asyncio.sleep(2)
                            continue
                        
                        # Atualizar no banco
                        home_clv = clv_data.get("home")
                        draw_clv = clv_data.get("draw")
                        away_clv = clv_data.get("away")
                        
                        for row in event_rows:
                            sel_lower = str(row.selection).lower()
                            closing_odd_sel = None
                            if "home" in sel_lower or "1" in sel_lower:
                                closing_odd_sel = home_clv
                            elif "draw" in sel_lower or "x" in sel_lower:
                                closing_odd_sel = draw_clv
                            elif "away" in sel_lower or "2" in sel_lower:
                                closing_odd_sel = away_clv
                                
                            upd = update(ValueOpportunityLog).where(
                                ValueOpportunityLog.id == row.id
                            ).values(
                                closing_odd_home=home_clv,
                                closing_odd_draw=draw_clv,
                                closing_odd_away=away_clv,
                                closing_odd_selection=closing_odd_sel,
                                clv_updated_at=datetime.now(timezone.utc)
                            )
                            await session.execute(upd)
                        
                        await session.commit()
                        logger.info("CLV persistido com sucesso para o evento %s", event_id)
                        
                        await asyncio.sleep(2)  # Respeito ao Rate Limit da BetsAPI
                        
            except Exception as e:
                logger.error("Erro no ciclo do CLV tracker: %s", e)
            
            logger.info("Ciclo concluído. Dormindo 300 segundos...")
            await asyncio.sleep(300)

if __name__ == "__main__":
    if not BETSAPI_KEY:
        logger.error("Variável BETSAPI_KEY não definida.")
    asyncio.run(run_clv_extraction())
