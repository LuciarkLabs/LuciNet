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
        self.active_workers = []
        self.current_queue = None

    def cancel(self):

        self.is_cancelled = True

        for w in self.active_workers:
            if not w.done():
                w.cancel()

        if self.current_queue:
            while not self.current_queue.empty():
                try:
                    self.current_queue.get_nowait()
                    self.current_queue.task_done()
                except asyncio.QueueEmpty:
                    break

    async def scan_all(
        self,
        proxies: List[ProxyConfig],
        on_progress: Callable[[ProxyConfig, dict], None],
        concurrent_scans: int = 50,
        timeout_seconds: int = 15,
    ):
        self.is_cancelled = False
        self.runner.set_concurrent_limit(concurrent_scans)
        self.runner.checker.set_timeout(timeout_seconds)

        self.current_queue = asyncio.Queue()
        for p in proxies:
            self.current_queue.put_nowait(p)

        async def worker():
            while True:
                try:
                    proxy = await self.current_queue.get()
                except asyncio.CancelledError:
                    break

                try:
                    if self.is_cancelled:
                        continue

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
                    break
                except Exception as e:
                    logger.error(f"Error in scan task for {proxy.remark}: {e}")
                finally:
                    self.current_queue.task_done()

        self.active_workers = [
            asyncio.create_task(worker()) for _ in range(concurrent_scans)
        ]
        await self.current_queue.join()

        for w in self.active_workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(*self.active_workers, return_exceptions=True)

        await self.repository.save_many(proxies)
        logger.info(
            f"Batch scan finished (or stopped) and saved {len(proxies)} proxies."
        )

    async def test_speed(self, proxy: ProxyConfig, max_size_kb: int = 500) -> float:
        self.runner.set_concurrent_limit(1)
        speed = await self.runner.check_download_speed(proxy, max_size_kb)
        proxy.download_speed = speed
        return speed

    async def test_speed_many(
        self, proxies: List[ProxyConfig], on_progress=None, max_size_kb: int = 500
    ):
        self.is_cancelled = False
        concurrent_scans = 5
        self.runner.set_concurrent_limit(concurrent_scans)

        self.current_queue = asyncio.Queue()
        for p in proxies:
            self.current_queue.put_nowait(p)

        async def worker():
            while True:
                try:
                    proxy = await self.current_queue.get()
                except asyncio.CancelledError:
                    break

                try:
                    if self.is_cancelled:
                        continue

                    speed = await self.runner.check_download_speed(proxy, max_size_kb)
                    proxy.download_speed = speed
                    if on_progress:
                        if asyncio.iscoroutinefunction(on_progress):
                            await on_progress(proxy)
                        else:
                            on_progress(proxy)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Speed test error: {e}")
                finally:
                    self.current_queue.task_done()

        self.active_workers = [
            asyncio.create_task(worker()) for _ in range(concurrent_scans)
        ]
        await self.current_queue.join()

        for w in self.active_workers:
            if not w.done():
                w.cancel()
        await asyncio.gather(*self.active_workers, return_exceptions=True)

        await self.repository.save_many(proxies)
        logger.info(
            f"Speed test finished (or stopped) and saved {len(proxies)} proxies."
        )
