import asyncio
import aiohttp
import itertools
import logging
import time
from collections import deque
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class ProxyRotator:
    """
    Gerencia a rotação de proxies para requisições HTTP assíncronas,
    incluindo um pool de conexão persistente e quarentena para proxies falhos.
    """

    def __init__(self, proxies: List[Dict[str, str]]):
        if not proxies:
            raise ValueError("A lista de proxies não pode estar vazia.")
        
        self.all_proxies_config = proxies
        self.active_proxies = deque()
        self.proxy_auth_map: Dict[str, Optional[aiohttp.BasicAuth]] = {}
        
        for p in proxies:
            proxy_url = self._build_proxy_url(p)
            self.active_proxies.append(proxy_url)
            if 'user' in p and 'pass' in p:
                self.proxy_auth_map[proxy_url] = aiohttp.BasicAuth(login=p['user'], password=p['pass'])
            else:
                self.proxy_auth_map[proxy_url] = None

        self.quarantined_proxies: Dict[str, float] = {} # {proxy_url: timestamp_fim_quarentena}
        self.client_session: Optional[aiohttp.ClientSession] = None
        self.lock = asyncio.Lock()
        logger.info(f"ProxyRotator inicializado com {len(self.all_proxies_config)} proxies. {len(self.active_proxies)} ativos.")

    async def __aenter__(self):
        """Inicializa a sessão aiohttp ao entrar no contexto assíncrono."""
        await self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fecha a sessão aiohttp ao sair do contexto assíncrono."""
        await self._release_session()
        
    async def _create_session(self):
        """Cria uma única aiohttp.ClientSession de longa duração."""
        if self.client_session is None or self.client_session.closed:
            connector = aiohttp.TCPConnector(ssl=False) 
            self.client_session = aiohttp.ClientSession(connector=connector)
            logger.info("aiohttp.ClientSession de longa duração criada.")

    async def _release_session(self):
        """Fecha a aiohttp.ClientSession."""
        if self.client_session and not self.client_session.closed:
            await self.client_session.close()
            self.client_session = None
            logger.info("aiohttp.ClientSession de longa duração fechada.")

    def _build_proxy_url(self, proxy_config: Dict[str, str]) -> str:
        """Constrói a URL do proxy sem autenticação embutida."""
        return f"http://{proxy_config['host']}:{proxy_config['port']}"

    async def get_client_session(self) -> aiohttp.ClientSession:
        """Retorna a sessão aiohttp de longa duração."""
        if self.client_session is None or self.client_session.closed:
            await self._create_session()
        return self.client_session

    async def get_next_proxy_details(self) -> Optional[Tuple[str, Optional[aiohttp.BasicAuth]]]:
        """
        Retorna a URL do próximo proxy e seu objeto de autenticação.
        Gerencia a quarentena de proxies.
        """
        async with self.lock:
            self._cleanup_quarantine()
            if not self.active_proxies:
                logger.warning("Nenhum proxy ativo disponível para rotação.")
                return None
            
            # Rotaciona para o próximo proxy
            proxy_url = self.active_proxies[0]
            self.active_proxies.rotate(-1) # Move o primeiro para o final
            
            proxy_auth = self.proxy_auth_map.get(proxy_url)
            
            logger.debug(f"Usando proxy: {proxy_url}")
            return proxy_url, proxy_auth

    async def mark_proxy_bad(self, proxy_url: str):
        """
        Marca um proxy como falho e o coloca em quarentena por 5 minutos.
        """
        async with self.lock:
            if proxy_url in self.active_proxies:
                self.active_proxies.remove(proxy_url)
            self.quarantined_proxies[proxy_url] = time.time() + 300 # 5 minutos de quarentena
            logger.warning(f"Proxy '{proxy_url}' marcado como falho e em quarentena por 5 minutos.")

    def _cleanup_quarantine(self):
        """
        Move proxies da quarentena de volta para a lista ativa se o tempo de quarentena expirou.
        """
        now = time.time()
        to_reactivate = []
        for proxy_url, quarantine_end_time in self.quarantined_proxies.items():
            if now >= quarantine_end_time:
                to_reactivate.append(proxy_url)
        
        for proxy_url in to_reactivate:
            self.quarantined_proxies.pop(proxy_url)
            # Verifica se o proxy já não está ativo (pode ter sido re-adicionado manualmente)
            if proxy_url not in self.active_proxies:
                self.active_proxies.append(proxy_url)
            logger.info(f"Proxy '{proxy_url}' removido da quarentena e reativado.")
