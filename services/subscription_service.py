import aiohttp
import base64
import time
from typing import Tuple, List

from domain.subscription import Subscription
from domain.proxy import ProxyConfig
from repository.base_repo import BaseProxyRepository

from parser.exceptions import ParseError
from utils.logger import get_logger

logger = get_logger("SubscriptionService")

class SubscriptionService:
    def __init__(self, repository: BaseProxyRepository, proxy_parser):
\
\
\

        self.repository = repository
        self.parser = proxy_parser

    async def fetch_and_update(self, sub: Subscription) -> Tuple[bool, int, str]:
\
\
\

        try:

            async with aiohttp.ClientSession() as session:
                async with session.get(sub.url, timeout=15) as response:
                    if response.status != 200:
                        return False, 0, f"HTTP Error: {response.status}"
                    raw_data = await response.text()

            decoded_data = self._decode_data(raw_data)

            lines = decoded_data.splitlines()
            new_proxies: List[ProxyConfig] = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                try:

                    proxy = self.parser.parse_url(line)

                    if proxy:

                        proxy.sub_id = sub.id
                        proxy.group_name = sub.name
                        new_proxies.append(proxy)
                except ParseError as e:

                    logger.debug(f"Skipping invalid proxy line: {e}")
                    continue

            if not new_proxies:
                return False, 0, "هیچ کانفیگ معتبری در این لینک یافت نشد."

            if sub.id is None:
                sub.last_update = time.time()
                sub.id = await self.repository.save_subscription(sub)
                for p in new_proxies:
                    p.sub_id = sub.id
            else:
                await self.repository.delete_proxies_by_sub(sub.id)

            await self.repository.save_many(new_proxies)

            sub.last_update = time.time()
            await self.repository.save_subscription(sub)

            logger.info(
                f"Subscription '{sub.name}' updated successfully with {len(new_proxies)} proxies."
            )
            return True, len(new_proxies), ""

        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching subscription: {e}")
            return False, 0, "خطا در اتصال به شبکه یا لینک سابسکریپشن."
        except Exception as e:
            logger.error(f"Subscription update failed: {e}")
            return False, 0, str(e)

    def _decode_data(self, data: str) -> str:
\
\
\

        data = data.strip()

        padding_needed = len(data) % 4
        if padding_needed:
            data += "=" * (4 - padding_needed)

        try:
            decoded_bytes = base64.b64decode(data, validate=True)
            return decoded_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return data
