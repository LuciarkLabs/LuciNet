from PySide6.QtCore import QObject, Signal
from gui.workers import SpeedTestWorker, AsyncTaskWorker


class SpeedManager(QObject):
    state_changed = Signal(bool)
    progress_updated = Signal(int, int, object)
    finished = Signal(bool)
    single_result_ready = Signal(object, float)
    error_occurred = Signal(str)

    def __init__(self, scan_service, repository):
        super().__init__()
        self.scan_service = scan_service
        self.repository = repository

        self.worker = None
        self._worker_save = None

        self.is_running = False
        self.is_stopped = False
        self.total = 0
        self.current = 0

    def test_multiple(self, proxies, max_size_kb):
        if self.is_running or not proxies:
            return

        self.is_running = True
        self.is_stopped = False
        self.total = len(proxies)
        self.current = 0

        self.state_changed.emit(True)

        self.worker = SpeedTestWorker(
            self.scan_service, proxies, max_size_kb=max_size_kb
        )
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, proxy):
        self.current += 1
        self.progress_updated.emit(self.current, self.total, proxy)

    def _on_finished(self):
        self.is_running = False
        self.state_changed.emit(False)
        self.finished.emit(self.is_stopped)

    def test_single(self, proxy, max_size_kb):
        if self.is_running:
            return

        self.is_running = True
        self.is_stopped = False
        self.state_changed.emit(True)

        self.worker = AsyncTaskWorker(
            self.scan_service.test_speed(proxy, max_size_kb=max_size_kb)
        )
        self.worker.finished_signal.connect(
            lambda speed: self._on_single_tested(proxy, speed)
        )
        self.worker.error_signal.connect(self._on_single_test_error)
        self.worker.start()

    def _on_single_test_error(self, err_msg):
        self.is_running = False
        self.state_changed.emit(False)
        self.error_occurred.emit(str(err_msg))

    def _on_single_tested(self, proxy, speed):
        self._worker_save = AsyncTaskWorker(self.repository.save(proxy))
        self._worker_save.finished_signal.connect(
            lambda _: self._on_single_saved(proxy, speed)
        )
        self._worker_save.error_signal.connect(
            self._on_single_test_error
        )
        self._worker_save.start()

    def _on_single_saved(self, proxy, speed):
        self.is_running = False
        self.state_changed.emit(False)
        self.single_result_ready.emit(proxy, speed)

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
