from domain.models.raw_config import RawXrayConfig
from PySide6.QtCore import QObject, Signal
from gui.workers import AsyncTaskWorker


class ToolsManager(QObject):
    action_state_changed = Signal(bool)
    action_finished = Signal(
        str, int
    )
    error_occurred = Signal(str)

    request_confirmation = Signal(str, int, list, list)

    def __init__(self, repository):
        super().__init__()
        self.repository = repository

        self.is_running = False
        self._action_worker = None

    def execute_move(self, proxy_ids, raw_ids, target_group):
        if (not proxy_ids and not raw_ids) or self.is_running:
            return

        self.is_running = True
        self.action_state_changed.emit(True)

        async def _move_all():
            return await self.repository.move_mixed_many(proxy_ids, raw_ids, target_group)

        self._action_worker = AsyncTaskWorker(_move_all())
        self._action_worker.finished_signal.connect(
            lambda count: self._on_action_success("move", count)
        )
        self._action_worker.error_signal.connect(self._on_action_error)
        self._action_worker.start()

    def execute_delete(self, proxy_ids, raw_ids, action_type="delete"):
        if (not proxy_ids and not raw_ids) or self.is_running:
            return

        self.is_running = True
        self.action_state_changed.emit(True)

        async def _delete_all():
            return await self.repository.delete_mixed_many(proxy_ids, raw_ids)

        self._action_worker = AsyncTaskWorker(_delete_all())
        self._action_worker.finished_signal.connect(
            lambda count: self._on_action_success(action_type, count)
        )
        self._action_worker.error_signal.connect(self._on_action_error)
        self._action_worker.start()

    def prepare_delete_invalid(self, all_proxies, current_group_filter):
        """پیدا کردن پراکسی‌های نامعتبر و درخواست تایید از View"""
        if self.is_running:
            return

        proxy_ids = []
        raw_ids = []
        for p in all_proxies:
            if not current_group_filter or p.group_name == current_group_filter:
                st = getattr(p, "status", None)
                if st in ("Invalid", "Error"):
                    if isinstance(p, RawXrayConfig) or getattr(p, "is_raw", False):
                        if p.id:
                            raw_ids.append(p.id)
                    else:
                        if p.id:
                            proxy_ids.append(p.id)

        total_count = len(proxy_ids) + len(raw_ids)
        if total_count == 0:
            self.error_occurred.emit("arc_msg_no_invalid")
            return

        self.request_confirmation.emit("delete_invalid", total_count, proxy_ids, raw_ids)

    def prepare_delete_timeout(self, all_proxies, current_group_filter):
        """پیدا کردن پراکسی‌های تایم‌اوت شده و درخواست تایید از View"""
        if self.is_running:
            return

        proxy_ids = []
        raw_ids = []
        for p in all_proxies:
            if not current_group_filter or p.group_name == current_group_filter:
                st = getattr(p, "status", None)
                if st == "Timeout":
                    if isinstance(p, RawXrayConfig) or getattr(p, "is_raw", False):
                        if p.id:
                            raw_ids.append(p.id)
                    else:
                        if p.id:
                            proxy_ids.append(p.id)

        total_count = len(proxy_ids) + len(raw_ids)
        if total_count == 0:
            self.error_occurred.emit("arc_msg_no_timeout")
            return

        self.request_confirmation.emit("delete_timeout", total_count, proxy_ids, raw_ids)

    def prepare_remove_duplicates(self, all_proxies, current_group_filter):
        """الگوریتم پیدا کردن پراکسی‌های تکراری و درخواست تایید از View"""
        if self.is_running:
            return

        proxies_to_check = [
            p
            for p in all_proxies
            if not isinstance(p, RawXrayConfig)
            and not getattr(p, "is_raw", False)
            and (not current_group_filter or p.group_name == current_group_filter)
        ]

        raw_to_check = [
            p
            for p in all_proxies
            if (isinstance(p, RawXrayConfig) or getattr(p, "is_raw", False))
            and (not current_group_filter or p.group_name == current_group_filter)
        ]

        sorted_proxies = sorted(
            proxies_to_check,
            key=lambda x: (
                0 if getattr(x, "status", None) == "Valid" else 1,
                x.ping if getattr(x, "ping", 0) > 0 else float("inf"),
            ),
        )

        seen_signatures = set()
        to_delete_ids = []

        for p in sorted_proxies:
            signature = (
                p.protocol.lower(),
                p.server.lower(),
                p.port,
                p.uuid_pwd,
                p.network.lower() if p.network else "",
                p.security.lower() if p.security else "",
                p.path.strip() if p.path else "",
                p.sni.lower() if p.sni else "",
                p.pbk.strip() if p.pbk else "",
            )

            if signature in seen_signatures:
                if p.id:
                    to_delete_ids.append(p.id)
            else:
                seen_signatures.add(signature)

        sorted_raw = sorted(
            raw_to_check,
            key=lambda x: (
                0 if getattr(x, "status", None) == "Valid" else 1,
                x.ping if getattr(x, "ping", 0) > 0 else float("inf"),
            ),
        )
        seen_raw_hashes = set()
        to_delete_raw_ids = []
        for r in sorted_raw:
            h = r.unique_hash
            if h in seen_raw_hashes:
                if r.id:
                    to_delete_raw_ids.append(r.id)
            else:
                seen_raw_hashes.add(h)

        total_dups = len(to_delete_ids) + len(to_delete_raw_ids)
        if total_dups == 0:
            self.error_occurred.emit("arc_msg_no_dedup")
            return

        self.request_confirmation.emit(
            "remove_duplicates", total_dups, to_delete_ids, to_delete_raw_ids
        )

    def _on_action_success(self, action_type, count):
        self.is_running = False
        self.action_state_changed.emit(False)
        self.action_finished.emit(action_type, count)

    def _on_action_error(self, err_msg):
        self.is_running = False
        self.action_state_changed.emit(False)
        self.error_occurred.emit(str(err_msg))
