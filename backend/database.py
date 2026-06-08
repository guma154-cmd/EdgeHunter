import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
import logging
import os
import json

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base para os modelos declarativos do SQLAlchemy
Base = declarative_base()

class ValueOpportunityLog(Base):
    """
    Modelo SQLAlchemy para registrar oportunidades de valor detectadas.
    Otimizado para PostgreSQL com tipos de dados apropriados e índices.
    """
    __tablename__ = 'value_opportunity_log'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    event_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False, comment="ID único do evento esportivo")
    bookmaker: Mapped[str] = mapped_column(String(100), index=True, nullable=False, comment="Casa de apostas onde a oportunidade foi encontrada")
    market_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="Tipo de mercado (ex: 'Match Odds', 'Over/Under 2.5')")
    selection: Mapped[str] = mapped_column(String(255), nullable=False, comment="Seleção específica dentro do mercado (ex: 'Time A Vence', 'Mais de 2.5 Gols')")
    odd: Mapped[float] = mapped_column(Float, nullable=False, comment="Odd detectada na casa de apostas")
    true_probability: Mapped[float] = mapped_column(Float, nullable=False, comment="Probabilidade 'verdadeira' estimada após remoção de overround (Power Method)")
    value_edge: Mapped[float] = mapped_column(Float, nullable=False, comment="Vantagem de valor (odd * true_probability - 1)")
    stake: Mapped[float] = mapped_column(Float, nullable=False, comment="Aposta calculada pelo Critério de Kelly Fracionário")
    bankroll_snapshot: Mapped[float] = mapped_column(Float, nullable=False, comment="Snapshot do saldo da banca no momento da detecção")
    match_details: Mapped[dict] = mapped_column(JSONB, nullable=True, comment="Detalhes completos do jogo em formato JSON ou texto")
    raw_odds_source: Mapped[dict] = mapped_column(JSONB, nullable=True, comment="Dados brutos das odds que geraram esta oportunidade (JSON)")
    closing_odd_home: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    closing_odd_draw: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    closing_odd_away: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    closing_odd_selection: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    btcl_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    clv_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self):
        return (f"<ValueOpportunityLog(id={self.id}, event_id='{self.event_id}', "
                f"bookmaker='{self.bookmaker}', selection='{self.selection}', "
                f"value_edge={self.value_edge:.4f})>")


class OddsHistory(Base):
    """
    Historico bruto de odds 1X2 extraidas para backtesting e CLV.
    Registra todo evento consumido pelo worker, mesmo sem oportunidade validada.
    """
    __tablename__ = 'odds_history'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    event_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False, comment="ID unico do evento esportivo")
    league: Mapped[str] = mapped_column(String(255), index=True, nullable=True, comment="Liga/competicao do evento")
    home_team: Mapped[str] = mapped_column(String(255), nullable=True, comment="Time mandante")
    away_team: Mapped[str] = mapped_column(String(255), nullable=True, comment="Time visitante")
    bookmaker: Mapped[str] = mapped_column(String(100), index=True, nullable=False, comment="Fonte/casa das odds")
    market_type: Mapped[str] = mapped_column(String(100), nullable=False, default="1X2", comment="Mercado das odds")
    event_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, comment="Horario previsto do evento")
    home_odd: Mapped[float] = mapped_column(Float, nullable=False, comment="Odd do mandante")
    draw_odd: Mapped[float] = mapped_column(Float, nullable=False, comment="Odd do empate")
    away_odd: Mapped[float] = mapped_column(Float, nullable=False, comment="Odd do visitante")
    raw_odds_source: Mapped[dict] = mapped_column(JSONB, nullable=True, comment="Payload bruto que originou a linha historica")

    def __repr__(self):
        return (f"<OddsHistory(id={self.id}, event_id='{self.event_id}', "
                f"home_odd={self.home_odd:.4f}, draw_odd={self.draw_odd:.4f}, "
                f"away_odd={self.away_odd:.4f})>")


class OddsTimeSeries(Base):
    """
    Serie temporal de odds 1X2 capturadas continuamente por bookmaker.
    """
    __tablename__ = "odds_time_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    sport_key: Mapped[str] = mapped_column(String(100), nullable=False)
    home_team: Mapped[str] = mapped_column(String(255), nullable=False)
    away_team: Mapped[str] = mapped_column(String(255), nullable=False)
    commence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capture_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    bookmaker: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    home_odd: Mapped[float] = mapped_column(Float, nullable=False)
    draw_odd: Mapped[float] = mapped_column(Float, nullable=False)
    away_odd: Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self):
        return (f"<OddsTimeSeries(id={self.id}, event_id='{self.event_id}', "
                f"bookmaker='{self.bookmaker}', capture_timestamp={self.capture_timestamp})>")

# Configuração do banco de dados (deve vir de variáveis de ambiente)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/edgehunter_db")

class AsyncDatabase:
    def __init__(self, db_url: str = DATABASE_URL):
        self.engine = create_async_engine(db_url, echo=False) # echo=True para ver as queries SQL
        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False, # Não expira objetos após o commit
            class_=AsyncSession
        )

    async def init_db(self):
        """Cria as tabelas no banco de dados, se não existirem."""
        logging.info("Inicializando o banco de dados...")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logging.info("Banco de dados inicializado.")

    async def get_session(self) -> AsyncSession:
        """Fornece uma sessão assíncrona para operações de banco de dados."""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()
