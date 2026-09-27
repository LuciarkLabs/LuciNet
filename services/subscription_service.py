import aiohttp
import base64
import time
from typing import Tuple, List

from domain.subscription import Subscription
from domain.proxy import ProxyConfig
from repository.base_repo import BaseProxyRepository
from domain.models.raw_config import RawXrayConfig
from parser.json_detector import JsonDetector, JsonConfigType

from parser.exceptions import ParseError
from utils.logger import get_logger

logger = get_logger("SubscriptionService")


class SubscriptionService:
    def __init__(self, repository: BaseProxyRepository, proxy_parser):
        """
        repository: برای ارتباط با دیتابیس
        proxy_parser: اینستنسی از ParserFactory
        """
        self.repository = repository
        self.parser = proxy_parser

    async def fetch_and_update(self, sub: Subscription) -> Tuple[bool, int, str]:
        """
        دریافت لینک، پارس کردن کانفیگ‌ها و آپدیت دیتابیس
        خروجی: (وضعیت موفقیت، تعداد کانفیگ‌های اضافه شده، پیام خطا)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sub.url, timeout=15) as response:
                    if response.status != 200:
                        return False, 0, f"HTTP Error: {response.status}"
                    raw_data = await response.text()

            detect_res = JsonDetector.detect(raw_data)
            payload_to_save = raw_data
            
            decoded_data = self._decode_data(raw_data)
            if detect_res == JsonConfigType.INVALID_OR_NOT_XRAY:
                detect_res = JsonDetector.detect(decoded_data)
                if detect_res != JsonConfigType.INVALID_OR_NOT_XRAY:
                    payload_to_save = decoded_data
                    
            if detect_res == JsonConfigType.FULL_XRAY_CONFIG:
                raw_config = RawXrayConfig(
                    name=sub.name,
                    raw_payload=payload_to_save,
                    group_name=sub.name,
                    source_type="subscription",
                    source_ref=sub.url,
                    sub_id=sub.id
                )
                
                sub.last_update = time.time()
                await self.repository.update_subscription_transactional(sub, proxies=None, raw_config=raw_config)
                
                logger.info(f"Subscription '{sub.name}' updated successfully as Raw JSON Config.")
                return True, 1, ""

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

            sub.last_update = time.time()
            await self.repository.update_subscription_transactional(sub, proxies=new_proxies, raw_config=None)

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
        """
        تلاش برای دیکد کردن Base64 (پشتیبانی از چندخطی، urlsafe و بدون پدینگ).
        اگر دیتا Base64 نبود (لینک‌های خام بود)، متن اصلی بازگردانده می‌شود.
        """
        raw_text = data.strip()
        if not raw_text:
            return raw_text

        first_line = raw_text.splitlines()[0].strip().lower()
        if any(
            first_line.startswith(proto)
            for proto in (
                "vless://",
                "vmess://",
                "trojan://",
                "ss://",
                "ssr://",
                "tuic://",
                "hysteria://",
                "hysteria2://",
                "hy2://",
                "{",
            )
        ):
            return raw_text

        cleaned = "".join(raw_text.split())
        cleaned = cleaned.replace("-", "+").replace("_", "/")
        padding_needed = (4 - len(cleaned) % 4) % 4
        cleaned += "=" * padding_needed

        try:
            decoded_bytes = base64.b64decode(cleaned)
            decoded_str = decoded_bytes.decode("utf-8", errors="replace")
            if "\x00" in decoded_str:
                return raw_text
            return decoded_str
        except Exception:
            return raw_text
