import time
import asyncio
import aiohttp
from domain.scan_result import ScanResult
from config import AppConfig
from utils.logger import get_logger

logger = get_logger("Checker")

class XrayChecker:
    def __init__(self, geoip_service):
        self.geoip_service = geoip_service
        self.timeout_seconds = AppConfig.SCAN_TIMEOUT_SECONDS

    def set_timeout(self, timeout: int):

        self.timeout_seconds = timeout

    async def check_connection(self, local_port: int) -> ScanResult:
        start_time = time.time()
        try:
            proxy_url = f"http://127.0.0.1:{local_port}"
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "*/*",
                    "Connection": "keep-alive",
                }
                test_url = "http://www.gstatic.com/generate_204"

                async with session.get(
                    test_url, proxy=proxy_url, headers=headers, allow_redirects=False
                ) as response:
                    if response.status not in (200, 204, 301, 302):
                        return ScanResult(
                            status="Invalid", error_message=f"HTTP {response.status}"
                        )

                latency_ms = round((time.time() - start_time) * 1000, 2)

                outbound_ip = ""
                try:
                    async with session.get(
                        "http://api.ipify.org?format=json",
                        proxy=proxy_url,
                        headers=headers,
                    ) as ip_resp:
                        if ip_resp.status == 200:
                            ip_data = await ip_resp.json()
                            outbound_ip = ip_data.get("ip", "")
                except Exception:
                    pass

                country = ""
                city = ""
                isp = ""
                if (
                    outbound_ip
                    and hasattr(self, "geoip_service")
                    and self.geoip_service
                ):
                    geo_data = await self.geoip_service.get_ip_info(outbound_ip)
                    if geo_data:
                        country, city, isp = geo_data

                return ScanResult(
                    status="Valid",
                    latency_ms=latency_ms,
                    country=country,
                    city=city,
                    isp=isp,
                    outbound_ip=outbound_ip,
                )

        except asyncio.TimeoutError:
            return ScanResult(status="Timeout", error_message="Timeout")
        except Exception as e:
            logger.debug(
                f"Port {local_port} check failed: {type(e).__name__} - {str(e)}"
            )
            return ScanResult(status="Timeout", error_message="Timeout")

    async def check_speed(self, local_port: int) -> float:
        start_time = time.time()
        try:
            proxy_url = f"http://127.0.0.1:{local_port}"

            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:

                test_url = "http://speed.cloudflare.com/__down?bytes=2097152"
                async with session.get(test_url, proxy=proxy_url) as response:
                    if response.status == 200:
                        data = await response.read()
                        duration = time.time() - start_time
                        if duration > 0:

                            speed_bps = len(data) / duration
                            return round(speed_bps / (1024 * 1024), 2)
        except Exception as e:
            logger.debug(f"Speed test failed: {e}")
        return 0.0
