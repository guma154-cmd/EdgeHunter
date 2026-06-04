
import asyncio
import aiohttp
import aioredis
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from backend.proxy_rotator import ProxyRotator
from backend.utils.rate_limiter import RedisRateLimiter, QuotaExceededError
from backend.scrapers.betsapi_client import BetsAPIClient

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações (devem vir de variáveis de ambiente em um sistema real)
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
ODDS_QUEUE_KEY = 'raw_odds_queue'
BETSAPI_KEY = "" # DEIXAR EM BRANCO PARA USAR DADOS MOCKADOS

# Ligas de Interesse (Exemplo)
LEAGUES_OF_INTEREST = {
    "Brazil Serie A": 14,
    "England Premier League": 2,
}

# Exemplo de configuração de proxies
PROXY_LIST = [
    {'host': 'proxy1.example.com', 'port': '8080', 'user': 'user1', 'pass': 'pass1'},
    {'host': 'proxy2.example.com', 'port': '8080'},
    {'host': 'proxy3.example.com', 'port': '8080', 'user': 'user3', 'pass': 'pass3'},
]

class AsyncRadar:
    def __init__(
        self, 
        redis_host: str, 
        redis_port: int, 
        redis_db: int, 
        proxies: List[Dict[str, str]],
        betsapi_key: str,
        leagues: Dict[str, int]
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_client: aioredis.Redis = None
        self.proxy_rotator = ProxyRotator(proxies)
        self.rate_limiter: RedisRateLimiter = None
        self.betsapi_client = BetsAPIClient(betsapi_key, self.proxy_rotator, leagues)
        
    async def connect_redis(self):
        """Conecta ao cliente Redis assíncrono e inicializa o rate limiter."""
        try:
            self.redis_client = await aioredis.from_url(
                f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}",
                decode_responses=True
            )
            self.rate_limiter = RedisRateLimiter(
                redis_client=self.redis_client,
                max_requests_per_sec=2,
                max_requests_per_day=2000
            )
            logging.info("Conectado ao Redis e Rate Limiter inicializado.")
        except aioredis.RedisError as e:
            logging.error(f"Erro ao conectar ao Redis: {e}")
            raise

    async def close_redis(self):
        """Fecha a conexão com o Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logging.info("Conexão com o Redis fechada.")

    async def process_fixture(self, fixture: Dict[str, Any]):
        """
        Processa um único fixture: busca odds de outras fontes (se necessário)
        e publica no Redis.
        """
        # A lógica de buscar em outras fontes (Pinnacle, etc.) seria adicionada aqui.
        # Por enquanto, apenas publicamos os dados normalizados da BetsAPI.
        
        # Valida a cota ANTES de qualquer request que seria feito aqui
        await self.rate_limiter.check_limit()

        await self.publish_to_redis(fixture)

    async def publish_to_redis(self, data: Dict[str, Any]):
        """Publica os dados no Redis."""
        if not self.redis_client:
            logging.error("Cliente Redis não está conectado, tentando reconectar...")
            await self.connect_redis()
            if not self.redis_client:
                logging.critical("Falha crítica ao reconectar ao Redis. Desistindo da publicação.")
                return

        message = json.dumps(data, ensure_ascii=False)
        try:
            await self.redis_client.rpush(ODDS_QUEUE_KEY, message)
            logging.info(f"Fixture '{data.get('home_team')} vs {data.get('away_team')}' publicado no Redis.")
        except aioredis.RedisError as e:
            logging.error(f"Erro ao publicar no Redis: {e}. Tentando reconectar na próxima iteração.")
            # A reconexão agora é tratada no início da função
            self.redis_client = None # Força a reconexão na próxima chamada

    async def start_orchestrator(self):
        """
        Inicia o orquestrador que busca jogos e coordena o processamento.
        """
        await self.connect_redis()

        async with self.proxy_rotator:
            while True:
                try:
                    logging.info("Iniciando ciclo de busca de jogos com Janela de Alvo...")
                    
                    # 1. Valida a cota antes de buscar a lista de jogos
                    await self.rate_limiter.check_limit()
                    
                    # 2. Busca os próximos jogos das ligas de interesse
                    upcoming_fixtures = await self.betsapi_client.get_upcoming_fixtures(hours_ahead=4)

                    if not upcoming_fixtures:
                        logging.info("Nenhum jogo encontrado na janela de alvo. Aguardando próximo ciclo.")
                        await asyncio.sleep(60 * 5) # Espera 5 minutos se não houver jogos
                        continue

                    # 3. Cria tarefas para processar cada jogo
                    tasks = [self.process_fixture(fixture) for fixture in upcoming_fixtures]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, Exception) and not isinstance(result, QuotaExceededError):
                            logging.error(f"Falha em uma tarefa de processamento de fixture: {result}", exc_info=True)

                    logging.info("Ciclo de busca concluído. Aguardando 15 minutos para o próximo.")
                    await asyncio.sleep(60 * 15)

                except QuotaExceededError as e:
                    logging.warning(f"Cota da API excedida: {e.message}. Hibernando por 1 hora.")
                    await asyncio.sleep(e.retry_after or 3600)
                
                except asyncio.CancelledError:
                    logging.info("Orquestrador cancelado.")
                    break
                
                except Exception as e:
                    logging.critical(f"Erro inesperado no loop principal do orquestrador: {e}", exc_info=True)
                    logging.info("Aguardando 5 minutos antes de reiniciar o ciclo.")
                    await asyncio.sleep(300)
            
            await self.close_redis()

async def main():
    radar = AsyncRadar(
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        redis_db=REDIS_DB,
        proxies=PROXY_LIST,
        betsapi_key=BETSAPI_KEY,
        leagues=LEAGUES_OF_INTEREST
    )
    await radar.start_orchestrator()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Orquestrador interrompido pelo usuário.")
    except Exception as e:
        logging.critical(f"Erro fatal no orquestrador: {e}", exc_info=True)
