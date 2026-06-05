import asyncio
import time
from typing import Optional
import redis.asyncio as aioredis
import logging

logger = logging.getLogger(__name__)

class QuotaExceededError(Exception):
    """Exceção customizada para quando a cota de requisições é excedida."""
    def __init__(self, message: str, retry_after: int = 0):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)

class RedisRateLimiter:
    """
    Implementa um rate limiter assíncrono com Redis para cotas por segundo e diárias.
    Utiliza uma abordagem de contador com TTL (Time-To-Live).
    """
    def __init__(
        self,
        redis_client: aioredis.Redis,
        max_requests_per_sec: int,
        max_requests_per_day: int,
        prefix: str = "rate_limit"
    ):
        if not isinstance(redis_client, aioredis.Redis):
            raise TypeError("redis_client must be an instance of aioredis.Redis")
        
        self.redis = redis_client
        self.max_requests_per_sec = max_requests_per_sec
        self.max_requests_per_day = max_requests_per_day
        self.prefix = prefix
        logger.info(
            f"RedisRateLimiter inicializado com: "
            f"{max_requests_per_sec} reqs/sec, {max_requests_per_day} reqs/day."
        )

    async def check_limit(self):
        """
        Verifica e incrementa os contadores de rate limit de forma atômica.
        Levanta QuotaExceededError se algum limite for atingido.
        """
        current_timestamp = int(time.time())
        
        # Chaves para o Redis
        key_sec = f"{self.prefix}:sec:{current_timestamp}"
        
        today = time.strftime("%Y-%m-%d", time.gmtime(current_timestamp))
        key_day = f"{self.prefix}:day:{today}"

        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                # Incrementa o contador por segundo e define TTL de 2s para segurança
                pipe.incr(key_sec)
                pipe.expire(key_sec, 2)
                
                # Incrementa o contador diário e define TTL para o fim do dia
                seconds_until_midnight_utc = (24 * 3600) - (current_timestamp % (24 * 3600))
                pipe.incr(key_day)
                pipe.expire(key_day, seconds_until_midnight_utc)
                
                # Executa a transação
                results = await pipe.execute()

            count_sec = results[0]
            count_day = results[2]

            # Verifica se as cotas foram excedidas
            if count_sec > self.max_requests_per_sec:
                raise QuotaExceededError(
                    f"Cota por segundo excedida ({self.max_requests_per_sec} reqs/sec).",
                    retry_after=1
                )
            
            if count_day > self.max_requests_per_day:
                raise QuotaExceededError(
                    f"Cota diária excedida ({self.max_requests_per_day} reqs/day).",
                    retry_after=seconds_until_midnight_utc
                )

            logger.debug(f"Uso da cota: {count_sec}/{self.max_requests_per_sec} por segundo, "
                         f"{count_day}/{self.max_requests_per_day} por dia.")

        except aioredis.RedisError as e:
            logger.error(f"Erro no Redis ao verificar rate limit: {e}. Permitindo a requisição como fallback.", exc_info=True)
            # Em caso de falha do Redis, podemos optar por falhar aberto ou fechado.
            # Aqui, falhamos aberto para não interromper o serviço, mas logamos como erro.
            pass
        except QuotaExceededError:
            # Re-levanta a exceção para ser tratada pelo chamador
            raise
        except Exception as e:
            logger.error(f"Erro inesperado no rate limiter: {e}", exc_info=True)
            # Falha aberta em caso de erro desconhecido
            pass
