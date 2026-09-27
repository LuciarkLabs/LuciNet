from PySide6.QtCore import QObject, Signal
from gui.workers import AsyncTaskWorker


class DataManager(QObject):
    loading_state_changed = Signal(bool)
    data_loaded = Signal(list)
    groups_loaded = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.is_loading = False
        self.last_load_type = "all"

        self._data_worker = None
        self._groups_worker = None
        self._current_request_id = 0
        self._group_request_id = 0

    def load_groups(self):
        self._group_request_id += 1
        req_id = self._group_request_id

        self._groups_worker = AsyncTaskWorker(self.repository.get_groups())
        self._groups_worker.finished_signal.connect(
            lambda groups: self._on_groups_loaded(groups, req_id)
        )
        self._groups_worker.error_signal.connect(
            lambda err: self._on_groups_error(err, req_id)
        )
        self._groups_worker.start()

    def _on_groups_loaded(self, groups, req_id):
        if req_id != self._group_request_id:
            return
        self.groups_loaded.emit(groups)

    def _on_groups_error(self, err_msg, req_id):
        if req_id != self._group_request_id:
            return
        self.error_occurred.emit(str(err_msg))

    def load_all(self, target_group=""):
        self.last_load_type = "all"
        self._fetch_data(target_group, only_untested=False)

    def load_untested(self, target_group=""):
        self.last_load_type = "untested"
        self._fetch_data(target_group, only_untested=True)

    def refresh(self, target_group=""):
        if self.last_load_type == "untested":
            self.load_untested(target_group)
        else:
            self.load_all(target_group)

    def _fetch_data(self, target_group, only_untested):
        self._current_request_id += 1
        req_id = self._current_request_id

        self._set_loading(True)
        fetch_coro = (
            self.repository.get_all_unified()
            if hasattr(self.repository, "get_all_unified")
            else self.repository.get_all()
        )
        self._data_worker = AsyncTaskWorker(fetch_coro)
        self._data_worker.finished_signal.connect(
            lambda proxies: self._process_proxies(
                proxies, target_group, only_untested, req_id
            )
        )
        self._data_worker.error_signal.connect(lambda err: self._on_error(err, req_id))
        self._data_worker.start()

    def _process_proxies(self, proxies, target_group, only_untested, req_id):
        if req_id != self._current_request_id:
            return

        filtered_proxies = []
        for p in proxies:
            status = getattr(p, "status", "Untested") or "Untested"
            if only_untested and status != "Untested":
                continue
            if target_group and p.group_name != target_group:
                continue
            filtered_proxies.append(p)

        self._set_loading(False)
        self.data_loaded.emit(filtered_proxies)

    def _on_error(self, err_msg, req_id):
        if req_id != self._current_request_id:
            return
        self._set_loading(False)
        self.error_occurred.emit(str(err_msg))

    def _set_loading(self, state):
        self.is_loading = state
        self.loading_state_changed.emit(state)
