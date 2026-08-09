from abc import ABC, abstractmethod
from typing import Tuple, Dict
import aiohttp
from utils.logger import get_logger

logger = get_logger("GeoIP")

class BaseGeoIPProvider(ABC):
    @abstractmethod
    async def get_info(self, ip: str) -> Tuple[str, str, str]:

        pass

class IPInfoProvider(BaseGeoIPProvider):
    def __init__(self, token: str = ""):
        self.token = token

    async def get_info(self, ip: str) -> Tuple[str, str, str]:
        url = f"https://ipinfo.io/{ip}/json"
        if self.token:
            url += f"?token={self.token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return (
                            data.get("country", ""),
                            data.get("city", ""),
                            data.get("org", ""),
                        )
        except Exception as e:
            logger.error(f"IPInfo fetch failed for {ip}: {e}")
        return ("", "", "")

class GeoIPService:
    def __init__(self, provider: BaseGeoIPProvider):
        self.provider = provider
        self._cache: Dict[str, Tuple[str, str, str]] = {}

    async def get_ip_info(self, ip: str) -> Tuple[str, str, str]:
        if ip in self._cache:
            return self._cache[ip]

        info = await self.provider.get_info(ip)
        self._cache[ip] = info
        return info
