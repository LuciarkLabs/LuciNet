import asyncio
from typing import List, Callable
from domain.proxy import ProxyConfig
from scanner.xray_runner import XrayRunnerPool
from repository.base_repo import BaseProxyRepository
from utils.logger import get_logger

logger = get_logger("ScanService")

class ScanService:
    def __init__(self, runner_pool: XrayRunnerPool, repository: BaseProxyRepository):
        self.runner = runner_pool
        self.repository = repository
        self.is_cancelled = False
        self.active_tasks = []

    def cancel(self):

        self.is_cancelled = True
        for task in self.active_tasks:
            if not task.done():
                task.cancel()

    async def scan_all(
        self,
        proxies: List[ProxyConfig],
        on_progress: Callable[[ProxyConfig, dict], None],
        concurrent_scans: int = 50,
        timeout_seconds: int = 15,
    ):
        self.is_cancelled = False
        self.active_tasks = []
        self.runner.set_concurrent_limit(concurrent_scans)
        self.runner.checker.set_timeout(timeout_seconds)

        async def _scan_and_update(proxy: ProxyConfig):
            if self.is_cancelled:
                return
            try:
                result = await self.runner.scan_proxy(proxy)
                proxy.status = result.status
                proxy.ping = result.latency_ms
                proxy.country = result.country
                proxy.city = result.city
                proxy.isp = result.isp
                proxy.last_scan = result.scan_time
                if result.status == "Valid":
                    proxy.last_seen_alive = result.scan_time
                proxy.scan_count += 1

                meta_info = {"error": result.error_message}
                if asyncio.iscoroutinefunction(on_progress):
                    await on_progress(proxy, meta_info)
                else:
                    on_progress(proxy, meta_info)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in scan task for {proxy.remark}: {e}")

        for p in proxies:
            self.active_tasks.append(asyncio.create_task(_scan_and_update(p)))

        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
            self.active_tasks.clear()

            if not self.is_cancelled:
                await self.repository.save_many(proxies)
                logger.info(
                    f"Batch scan completed and saved for {len(proxies)} proxies."
                )

    async def test_speed(self, proxy: ProxyConfig) -> float:

        self.runner.set_concurrent_limit(1)
        speed = await self.runner.check_download_speed(proxy)
        proxy.download_speed = speed
        return speed

    async def test_speed_many(self, proxies: List[ProxyConfig], on_progress=None):
        self.is_cancelled = False
        self.active_tasks = []
        self.runner.set_concurrent_limit(5)

        async def _test_single(proxy):
            if self.is_cancelled:
                return
            try:
                speed = await self.runner.check_download_speed(proxy)
                proxy.download_speed = speed
                if on_progress:
                    if asyncio.iscoroutinefunction(on_progress):
                        await on_progress(proxy)
                    else:
                        on_progress(proxy)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Speed test error: {e}")

        for p in proxies:
            self.active_tasks.append(asyncio.create_task(_test_single(p)))

        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
            self.active_tasks.clear()

        if not self.is_cancelled:
            await self.repository.save_many(proxies)
            logger.info(f"Speed test completed and saved for {len(proxies)} proxies.")
