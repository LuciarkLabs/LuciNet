from PySide6.QtCore import QObject, Signal
from gui.workers import ScanWorker


class ScanManager(QObject):
    state_changed = Signal(bool)
    scan_started = Signal(int, bool)
    progress_updated = Signal(object)
    progress_text_updated = Signal(int, int, int)
    finished = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, scan_service):
        super().__init__()
        self.scan_service = scan_service
        self.worker = None

        self.is_running = False
        self.is_stopped = False
        self.is_deep_scan_phase = False

        self.total = 0
        self.current = 0
        self.current_scan_list = []

        self.concurrent_threads = 10
        self.timeout_seconds = 5
        self.deep_scan_enabled = False
        self.probe_mode = "http"

    def set_scan_params(self, concurrent, timeout, enable_deep_scan, probe_mode="http"):
        self.concurrent_threads = concurrent
        self.timeout_seconds = timeout
        self.deep_scan_enabled = enable_deep_scan
        self.probe_mode = probe_mode

    def start_scan(self, proxies, is_deep_scan_phase=False):
        if self.is_running or not proxies:
            return

        self.is_running = True
        self.is_stopped = False
        self.is_deep_scan_phase = is_deep_scan_phase
        self.total = len(proxies)
        self.current = 0

        if not is_deep_scan_phase:
            self.current_scan_list = proxies

        self.state_changed.emit(True)
        self.scan_started.emit(self.total, self.is_deep_scan_phase)

        self.worker = ScanWorker(
            self.scan_service,
            proxies,
            concurrent_scans=self.concurrent_threads,
            timeout_seconds=self.timeout_seconds,
            probe_mode=self.probe_mode,
        )
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, proxy, meta):
        self.current += 1
        ping = proxy.ping if hasattr(proxy, "ping") else -1
        self.progress_text_updated.emit(self.current, self.total, ping)
        self.progress_updated.emit(proxy)

    def _on_finished(self):
        if not self.is_stopped:
            if self.deep_scan_enabled and not self.is_deep_scan_phase:
                failed_proxies = [
                    p
                    for p in self.current_scan_list
                    if p.status in ["Timeout", "Invalid", "Error"]
                ]
                if failed_proxies:
                    self.is_running = False
                    self.start_scan(failed_proxies, is_deep_scan_phase=True)
                    return

        self.is_running = False
        self.is_deep_scan_phase = False
        self.state_changed.emit(False)
        self.finished.emit(self.is_stopped)

    def _on_error(self, err_msg):
        self.is_running = False
        self.is_deep_scan_phase = False
        self.state_changed.emit(False)
        self.error_occurred.emit(str(err_msg))

    def stop(self):
        if not self.is_running:
            return

        self.is_stopped = True
        if hasattr(self.scan_service, "cancel"):
            self.scan_service.cancel()

        if self.worker:
            try:
                self.worker.requestInterruption()
            except RuntimeError:
                pass
