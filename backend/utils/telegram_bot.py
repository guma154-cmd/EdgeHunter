import asyncio
import html
import logging
import os
from datetime import datetime, time, timezone
from typing import Any

import aiohttp
from sqlalchemy import func, select

from database import ValueOpportunityLog


logger = logging.getLogger(__name__)


class AsyncTelegramBot:
    def __init__(self) -> None:
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self) -> None:
        if self.session is not None and not self.session.closed:
            await self.session.close()

    async def _send_message(self, text: str, chat_id: str | None = None) -> None:
        if not self.token:
            logger.warning("Telegram desabilitado: TELEGRAM_BOT_TOKEN ausente.")
            return

        target_chat_id = chat_id or self.chat_id
        if not target_chat_id:
            logger.warning("Telegram desabilitado: TELEGRAM_CHAT_ID ausente.")
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            session = await self._get_session()
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status >= 400:
                    body = await response.text()
                    logger.error("Falha Telegram status=%s body=%s", response.status, body)
        except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError) as exc:
            logger.error("Erro de rede ao enviar mensagem Telegram: %s", exc, exc_info=True)
        except Exception as exc:
            logger.error("Erro inesperado ao enviar mensagem Telegram: %s", exc, exc_info=True)

    async def send_opportunity_alert(self, log_entry: Any, match_details: dict[str, Any] | None) -> None:
        if not self.token or not self.chat_id:
            logger.warning("Telegram desabilitado: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID ausente.")
            return

        details = match_details or {}
        home_team = details.get("home_team") or "Home"
        away_team = details.get("away_team") or "Away"
        game = f"{home_team} vs {away_team}"
        edge_pct = float(getattr(log_entry, "value_edge", 0.0)) * 100.0
        stake = float(getattr(log_entry, "stake", 0.0))

        text = (
            "<b>Nova oportunidade EdgeHunter</b>\n"
            f"<b>Jogo:</b> {html.escape(str(game))}\n"
            f"<b>Mercado:</b> {html.escape(str(getattr(log_entry, 'market_type', 'N/A')))}\n"
            f"<b>Selecao:</b> {html.escape(str(getattr(log_entry, 'selection', 'N/A')))}\n"
            f"<b>Odd:</b> {float(getattr(log_entry, 'odd', 0.0)):.2f}\n"
            f"<b>Edge:</b> {edge_pct:.2f}%\n"
            f"<b>Stake:</b> R$ {stake:.2f}"
        )

        await self._send_message(text)
        logger.info("Alerta Telegram enviado para event_id=%s", getattr(log_entry, "event_id", "unknown"))

    async def start_polling(self, redis_client, db_session_maker) -> None:
        if not self.token:
            logger.warning("Polling Telegram desabilitado: TELEGRAM_BOT_TOKEN ausente.")
            return

        offset = 0
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"

        while True:
            try:
                session = await self._get_session()
                params = {"timeout": 30, "offset": offset}
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=40)) as response:
                    if response.status >= 400:
                        body = await response.text()
                        logger.error("Falha getUpdates Telegram status=%s body=%s", response.status, body)
                        await asyncio.sleep(5)
                        continue

                    payload = await response.json()

                for update in payload.get("result", []):
                    offset = max(offset, int(update.get("update_id", 0)) + 1)
                    message = update.get("message") or {}
                    chat = message.get("chat") or {}
                    chat_id = str(chat.get("id", ""))
                    parts = str(message.get("text") or "").strip().split()
                    if not parts:
                        continue
                    command = parts[0].lower()

                    if self.chat_id and chat_id != str(self.chat_id):
                        logger.warning("Comando Telegram ignorado de chat_id nao autorizado=%s", chat_id)
                        continue

                    if command == "/ping":
                        await self._send_message("EdgeHunter Operante.", chat_id=chat_id)
                    elif command == "/status":
                        await self._send_status(redis_client, db_session_maker, chat_id=chat_id)
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError) as exc:
                logger.error("Erro de rede no polling Telegram: %s", exc, exc_info=True)
                await asyncio.sleep(5)
            except Exception as exc:
                logger.error("Erro inesperado no polling Telegram: %s", exc, exc_info=True)
                await asyncio.sleep(5)

    async def _send_status(self, redis_client, db_session_maker, chat_id: str) -> None:
        try:
            queue_len = await redis_client.llen("raw_odds_queue")
            today_start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)

            async with db_session_maker() as session:
                result = await session.execute(
                    select(func.count())
                    .select_from(ValueOpportunityLog)
                    .where(ValueOpportunityLog.timestamp >= today_start)
                )
                opportunities_today = int(result.scalar_one())

            text = (
                "<b>EdgeHunter Status</b>\n"
                f"<b>Fila Redis:</b> {queue_len}\n"
                f"<b>Oportunidades hoje:</b> {opportunities_today}\n"
                "<b>Estado:</b> Operante"
            )
            await self._send_message(text, chat_id=chat_id)
        except Exception as exc:
            logger.error("Erro ao montar status Telegram: %s", exc, exc_info=True)
            await self._send_message("<b>EdgeHunter Status</b>\nErro ao consultar metricas.", chat_id=chat_id)
