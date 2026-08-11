import asyncio
from PySide6.QtCore import QThread, Signal
from utils.logger import get_logger

logger = get_logger("UI_Workers")

class AsyncTaskWorker(QThread):
    finished_signal = Signal(object)
    error_signal = Signal(str)

    def __init__(self, coroutine):
        super().__init__()
        self.coroutine = coroutine

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.coroutine)
            self.finished_signal.emit(result)
        except Exception as e:
            logger.error(f"AsyncTaskWorker Error: {e}")
            self.error_signal.emit(str(e))
        finally:
            loop.close()

class ScanWorker(QThread):
    progress_signal = Signal(object, dict)
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(
        self, scan_service, proxies_to_scan, concurrent_scans, timeout_seconds
    ):
        super().__init__()
        self.scan_service = scan_service
        self.proxies = proxies_to_scan
        self.concurrent_scans = concurrent_scans
        self.timeout_seconds = timeout_seconds

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def on_progress(proxy, meta):
            self.progress_signal.emit(proxy, meta)

        try:
            loop.run_until_complete(
                self.scan_service.scan_all(
                    self.proxies,
                    on_progress,
                    concurrent_scans=self.concurrent_scans,
                    timeout_seconds=self.timeout_seconds,
                )
            )
        except Exception as e:
            logger.error(f"ScanWorker Error: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()
            loop.close()

class SpeedTestWorker(QThread):
    progress_signal = Signal(object)
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, scan_service, proxies, max_size_kb=500):
        super().__init__()
        self.scan_service = scan_service
        self.proxies = proxies
        self.max_size_kb = max_size_kb

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def on_progress(proxy):
            self.progress_signal.emit(proxy)

        try:

            loop.run_until_complete(
                self.scan_service.test_speed_many(
                    self.proxies, on_progress, max_size_kb=self.max_size_kb
                )
            )
        except Exception as e:
            logger.error(f"SpeedTestWorker Error: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.finished_signal.emit()
            loop.close()
