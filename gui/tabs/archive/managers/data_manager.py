from PySide6.QtCore import QObject, Signal
from gui.workers import AsyncTaskWorker


class DataManager(QObject):
    loading_state_changed = Signal(bool)
    data_loaded = Signal(list)
    groups_loaded = Signal(list)

    group_created = Signal(str)
    group_renamed = Signal(str)
    group_deleted = Signal()
    error_occurred = Signal(str)

    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.is_loading = False
        self.is_action_running = False

        self._data_worker = None
        self._groups_worker = None
        self._action_worker = None

        self._current_request_id = 0
        self._group_request_id = 0

    async def _fetch_all_items(self):
        proxies = await self.repository.get_all()
        if hasattr(self.repository, "get_all_raw_configs"):
            raws = await self.repository.get_all_raw_configs()
            proxies.extend(raws)
        return proxies

    def load_data(self, is_db_locked):
        if is_db_locked:
            return

        self._current_request_id += 1
        req_id = self._current_request_id

        self._set_loading(True)
        self._data_worker = AsyncTaskWorker(self._fetch_all_items())
        self._data_worker.finished_signal.connect(
            lambda proxies: self._on_data_loaded(proxies, req_id)
        )
        self._data_worker.error_signal.connect(lambda err: self._on_error(err, req_id))
        self._data_worker.start()

    def _on_data_loaded(self, proxies, req_id):
        if req_id != self._current_request_id:
            return
        self._set_loading(False)
        self.data_loaded.emit(proxies)
        self.load_groups()

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
        available_groups = sorted(list(set(groups)))
        self.groups_loaded.emit(available_groups)

    def _on_groups_error(self, err_msg, req_id):
        if req_id != self._group_request_id:
            return
        self.error_occurred.emit(str(err_msg))

    def create_group(self, new_name):
        if self.is_action_running or self.is_loading:
            return
        self.is_action_running = True
        self._set_loading(True)
        self._action_worker = AsyncTaskWorker(self.repository.add_group(new_name))
        self._action_worker.finished_signal.connect(
            lambda _: self._on_group_created(new_name)
        )
        self._action_worker.error_signal.connect(self._on_action_error)
        self._action_worker.start()

    def _on_group_created(self, new_name):
        self.is_action_running = False
        self._set_loading(False)
        self.group_created.emit(new_name)

    def rename_group(self, current_name, new_name):
        if self.is_action_running or self.is_loading:
            return
        self.is_action_running = True
        self._set_loading(True)
        self._action_worker = AsyncTaskWorker(
            self.repository.rename_group(current_name, new_name)
        )
        self._action_worker.finished_signal.connect(
            lambda _: self._on_group_renamed(new_name)
        )
        self._action_worker.error_signal.connect(self._on_action_error)
        self._action_worker.start()

    def _on_group_renamed(self, new_name):
        self.is_action_running = False
        self._set_loading(False)
        self.group_renamed.emit(new_name)

    def delete_group(self, group_name):
        if self.is_action_running or self.is_loading:
            return
        self.is_action_running = True
        self._set_loading(True)
        self._action_worker = AsyncTaskWorker(self.repository.delete_group(group_name))
        self._action_worker.finished_signal.connect(self._on_group_deleted)
        self._action_worker.error_signal.connect(self._on_action_error)
        self._action_worker.start()

    def _on_group_deleted(self, _):
        self.is_action_running = False
        self._set_loading(False)
        self.group_deleted.emit()

    def _on_action_error(self, err_msg):
        self.is_action_running = False
        self._set_loading(False)
        self.error_occurred.emit(str(err_msg))

    def _on_error(self, err_msg, req_id):
        if req_id != self._current_request_id:
            return
        self._set_loading(False)
        self.error_occurred.emit(str(err_msg))

    def _set_loading(self, state):
        self.is_loading = state
        self.loading_state_changed.emit(state)
