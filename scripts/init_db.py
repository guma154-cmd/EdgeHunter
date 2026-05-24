"""Initialize the EdgeHunter SQLite schema idempotently."""

from pathlib import Path
import os
import sys
import logging

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edgehunter.database.schema import (
    EXPECTED_INDEXES,
    EXPECTED_TABLES,
    ensure_schema,
    get_indexes,
    get_pragma_profile,
    get_schema_version,
    verify_schema,
)
try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - fallback for lean environments
    logger = logging.getLogger(__name__)


def main() -> None:
    """Initialize the SQLite database schema used by EdgeHunter."""
    db_path = os.getenv("DATABASE_PATH", "./edge_hunter.db")
    logger.info(f"Inicializando banco de dados em: {db_path}")
    
    # Aplicar schema
    success = ensure_schema(db_path)
    
    if not success:
        logger.error("Falha ao aplicar schema")
        sys.exit(1)
    
    # Verificar estado
    tables = verify_schema(db_path)
    version = get_schema_version(db_path)
    
    logger.info(f"Versão do schema: {version}")
    logger.info("Tabelas esperadas:")
    for table, exists in tables.items():
        status = "✅" if exists else "❌"
        logger.info(f"  {status} {table}")

    indexes = get_indexes(db_path)
    logger.info("Indices obrigatorios:")
    for index_name in EXPECTED_INDEXES:
        status = "✅" if index_name in indexes else "❌"
        logger.info(f"  {status} {index_name}")

    pragma_profile = get_pragma_profile(db_path)
    logger.info(f"PRAGMAs ativos: {pragma_profile}")

    if all(tables.values()) and len(tables) == len(EXPECTED_TABLES):
        logger.success("✅ Banco de dados inicializado com sucesso!")
        sys.exit(0)
    else:
        logger.error("❌ Algumas tabelas não foram criadas")
        sys.exit(1)


if __name__ == "__main__":
    main()
