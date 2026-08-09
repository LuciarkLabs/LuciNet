import asyncio
import socket
from utils.logger import get_logger
from config import AppConfig

logger = get_logger("PortManager")

class PortManager:
    def __init__(
        self, start_port: int = AppConfig.BASE_LOCAL_PORT, max_ports: int = 1000
    ):
        self.start_port = start_port
        self.max_ports = max_ports

        self._lock = None
        self._in_use = set()

    def reset(self):

        self._lock = asyncio.Lock()
        self._in_use.clear()

    async def _is_port_free_async(self, port: int) -> bool:
        try:

            server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", port)
            server.close()
            await server.wait_closed()
            return True
        except OSError:
            return False

    async def get_free_port(self) -> int:
        if self._lock is None:
            self.reset()

        async with self._lock:
            for port in range(self.start_port, self.start_port + self.max_ports):
                if port not in self._in_use:
                    is_free = await self._is_port_free_async(port)
                    if is_free:
                        self._in_use.add(port)
                        return port
            raise RuntimeError("No free ports available")

    async def release_port(self, port: int):
        if self._lock is None:
            return
        async with self._lock:
            self._in_use.discard(port)
