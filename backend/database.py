import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB # Importar JSONB
from datetime import datetime, timezone
import logging
import os

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

    def __repr__(self):
        return (f"<ValueOpportunityLog(id={self.id}, event_id='{self.event_id}', "
                f"bookmaker='{self.bookmaker}', selection='{self.selection}', "
                f"value_edge={self.value_edge:.4f})>")

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

# Exemplo de uso
async def main():
    db_manager = AsyncDatabase()
    await db_manager.init_db()

    # Exemplo de inserção de dados
    async with db_manager.AsyncSessionLocal() as session:
        new_log = ValueOpportunityLog(
            event_id="match_12345",
            bookmaker="Bet365",
            market_type="Match Odds",
            selection="Home Win",
            odd=2.10,
            true_probability=0.50,
            value_edge=0.05,
            stake=10.50,
            bankroll_snapshot=1000.00,
            match_details=json.dumps({"team_a": "Team A", "team_b": "Team B"}),
            raw_odds_source=json.dumps({"bookie_data": {"odd_home": 2.15, "odd_draw": 3.20, "odd_away": 3.50}})
        )
        session.add(new_log)
        await session.commit()
        logging.info(f"Oportunidade de valor registrada: {new_log}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"Erro fatal no exemplo do banco de dados: {e}", exc_info=True)
