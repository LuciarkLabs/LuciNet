from PySide6.QtCore import QObject, Signal
from gui.workers import AsyncTaskWorker


class SubManager(QObject):
    group_subs_evaluated = Signal(bool, int)
    state_changed = Signal(bool)

    update_started = Signal(str, int)
    update_finished = Signal()
    update_result_ready = Signal(int, list)
    error_occurred = Signal(str)

    def __init__(self, repository, sub_service):
        super().__init__()
        self.repository = repository
        self.sub_service = sub_service
        self.current_subs_in_group = []
        self.is_updating = False

        self._worker_check = None
        self._worker_fetch_all = None
        self._worker_update = None
        self._check_request_id = 0

    @property
    def current_subscription_count(self):
        """بازگرداندن تعداد واقعی ساب‌های گروه جاری برای دیالوگ تاییدیه و UI"""
        return len(self.current_subs_in_group)

    def evaluate_group_subscriptions(self, group_name):
        self._check_request_id += 1
        req_id = self._check_request_id

        self.current_subs_in_group = []

        if not group_name:
            self.group_subs_evaluated.emit(False, 0)
            return

        self.group_subs_evaluated.emit(False, 0)

        self._worker_check = AsyncTaskWorker(self.repository.get_subscriptions())
        self._worker_check.finished_signal.connect(
            lambda subs: self._on_subs_fetched(subs, group_name, req_id)
        )
        self._worker_check.error_signal.connect(
            lambda err: self._on_check_error(err, req_id)
        )
        self._worker_check.start()

    def _on_subs_fetched(self, all_subs, group_name, req_id):
        if req_id != self._check_request_id:
            return
        self.current_subs_in_group = [s for s in all_subs if s.name == group_name]
        count = len(self.current_subs_in_group)
        self.group_subs_evaluated.emit(count > 0, count)

    def _on_check_error(self, err_msg, req_id):
        if req_id != self._check_request_id:
            return
        self.current_subs_in_group = []
        self.group_subs_evaluated.emit(False, 0)
        self.error_occurred.emit(str(err_msg))

    def update_current(self):
        if not self.current_subs_in_group or self.is_updating:
            return

        self.is_updating = True
        self.state_changed.emit(True)
        self.update_started.emit("current", self.current_subscription_count)

        self._worker_update = AsyncTaskWorker(
            self._update_subs_task(self.current_subs_in_group)
        )
        self._worker_update.finished_signal.connect(self._on_update_task_finished)
        self._worker_update.error_signal.connect(self._on_update_error)
        self._worker_update.start()

    def update_all(self):
        if self.is_updating:
            return

        self.is_updating = True
        self.state_changed.emit(True)
        self.update_started.emit("fetch_all", 0)

        self._worker_fetch_all = AsyncTaskWorker(self.repository.get_subscriptions())
        self._worker_fetch_all.finished_signal.connect(self._start_update_all_task)
        self._worker_fetch_all.error_signal.connect(self._on_update_error)
        self._worker_fetch_all.start()

    def _start_update_all_task(self, all_subs):
        if not all_subs:
            self.is_updating = False
            self.state_changed.emit(False)
            self.update_finished.emit()
            self.error_occurred.emit("arc_msg_no_subs")
            return

        self.update_started.emit("update_all", len(all_subs))

        self._worker_update = AsyncTaskWorker(self._update_subs_task(all_subs))
        self._worker_update.finished_signal.connect(self._on_update_task_finished)
        self._worker_update.error_signal.connect(self._on_update_error)
        self._worker_update.start()

    async def _update_subs_task(self, subs_list):
        total_added = 0
        errors = []
        for sub in subs_list:
            success, count, err_msg = await self.sub_service.fetch_and_update(sub)
            if success:
                total_added += count
            else:
                errors.append(f"{sub.name}: {err_msg}")
        return total_added, errors

    def _on_update_task_finished(self, result):
        total_added, errors = result
        self.is_updating = False
        self.state_changed.emit(False)
        self.update_finished.emit()
        self.update_result_ready.emit(total_added, errors)

    def _on_update_error(self, err_msg):
        self.is_updating = False
        self.state_changed.emit(False)
        self.update_finished.emit()
        self.error_occurred.emit(str(err_msg))
