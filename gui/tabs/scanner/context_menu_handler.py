from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMenu, QMessageBox, QApplication, QInputDialog
from domain.models.raw_config import RawXrayConfig
from gui.widgets.qr_dialog import QRDialog
from gui.language_manager import LanguageManager
from gui.workers import AsyncTaskWorker
from gui.event_bus import event_bus


class ContextMenuHandler(QObject):
    error_occurred = Signal(str)
    state_changed = Signal(bool)

    def __init__(
        self,
        parent_widget,
        repository,
        speed_manager,
        scan_manager,
        table_view,
        model,
        proxy_model,
    ):
        super().__init__()
        self.parent_widget = parent_widget
        self.repository = repository
        self.speed_manager = speed_manager
        self.scan_manager = scan_manager
        self.table_view = table_view
        self.model = model
        self.proxy_model = proxy_model

        self.worker_action = None
        self.action_running = False

    def show_context_menu(self, pos, available_groups, speed_size):
        if (
            self.scan_manager.is_running
            or self.speed_manager.is_running
            or self.action_running
        ):
            return

        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return

        selected_indexes = self.table_view.selectionModel().selectedRows()
        selected_proxies = []
        for idx in selected_indexes:
            if not idx.isValid():
                continue
            source_index = self.proxy_model.mapToSource(idx)
            if not source_index.isValid():
                continue
            selected_proxies.append(self.model.proxies[source_index.row()])

        if not selected_proxies:
            return

        proxy = selected_proxies[0]
        menu = QMenu(self.parent_widget)

        if len(selected_proxies) == 1:
            action_copy = menu.addAction(LanguageManager.tr("scn_ctx_copy"))
            if not isinstance(proxy, RawXrayConfig) and not getattr(proxy, "is_raw", False):
                action_qr = menu.addAction(LanguageManager.tr("scn_ctx_qr"))
            else:
                action_qr = None
        else:
            action_copy = None
            action_qr = None

        action_speed = menu.addAction(
            LanguageManager.tr("scn_ctx_speed").format(count=len(selected_proxies))
        )
        menu.addSeparator()
        action_move = menu.addAction(
            LanguageManager.tr("scn_ctx_move").format(count=len(selected_proxies))
        )
        action_delete = menu.addAction(
            LanguageManager.tr("scn_ctx_delete").format(count=len(selected_proxies))
        )

        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))

        if action_copy and action == action_copy:
            self._copy_to_clipboard(proxy)
        elif action_qr and action == action_qr:
            self._show_qr_dialog(proxy)
        elif action == action_speed:
            self._trigger_speed_test(selected_proxies, speed_size)
        elif action == action_move:
            self._move_proxies(selected_proxies, available_groups)
        elif action == action_delete:
            self._delete_proxies(selected_proxies)

    def _copy_to_clipboard(self, proxy):
        payload = (
            proxy.raw_payload
            if isinstance(proxy, RawXrayConfig) or getattr(proxy, "is_raw", False)
            else proxy.raw_url
        )
        QApplication.clipboard().setText(payload)
        QMessageBox.information(
            self.parent_widget,
            LanguageManager.tr("scn_msg_copied_title"),
            LanguageManager.tr("scn_msg_copied_body"),
        )

    def _show_qr_dialog(self, proxy):
        if isinstance(proxy, RawXrayConfig) or getattr(proxy, "is_raw", False):
            return
        dialog = QRDialog(proxy.remark or "Config", proxy.raw_url, self.parent_widget)
        dialog.exec()

    def _trigger_speed_test(self, proxies, speed_size):
        if len(proxies) == 1:
            self.speed_manager.test_single(proxies[0], max_size_kb=speed_size)
        else:
            self.speed_manager.test_multiple(proxies, max_size_kb=speed_size)

    def _handle_worker_finish(self, _):
        self.action_running = False
        self.state_changed.emit(False)
        event_bus.data_changed.emit()

    def _handle_worker_error(self, err):
        self.action_running = False
        self.state_changed.emit(False)
        self.error_occurred.emit(str(err))

    def _move_proxies(self, proxies, available_groups):
        proxy_ids = [
            p.id
            for p in proxies
            if p.id and not isinstance(p, RawXrayConfig) and not getattr(p, "is_raw", False)
        ]
        raw_ids = [
            p.id
            for p in proxies
            if p.id and (isinstance(p, RawXrayConfig) or getattr(p, "is_raw", False))
        ]
        total_count = len(proxy_ids) + len(raw_ids)
        if total_count == 0:
            return

        groups = list(available_groups)
        if "Default" not in groups:
            groups.insert(0, "Default")

        msg = (
            LanguageManager.tr("scn_msg_move_single_prompt").format(
                remark=proxies[0].remark
            )
            if total_count == 1
            else LanguageManager.tr("scn_msg_move_multi_prompt").format(count=total_count)
        )

        new_group, ok = QInputDialog.getItem(
            self.parent_widget,
            LanguageManager.tr("scn_msg_move_title"),
            msg,
            groups,
            0,
            True,
        )

        if ok and new_group.strip():
            self.action_running = True
            self.state_changed.emit(True)
            self.worker_action = AsyncTaskWorker(
                self.repository.move_mixed_many(proxy_ids, raw_ids, new_group.strip())
            )
            self.worker_action.finished_signal.connect(self._handle_worker_finish)
            self.worker_action.error_signal.connect(self._handle_worker_error)
            self.worker_action.start()

    def _delete_proxies(self, proxies):
        proxy_ids = [
            p.id
            for p in proxies
            if p.id and not isinstance(p, RawXrayConfig) and not getattr(p, "is_raw", False)
        ]
        raw_ids = [
            p.id
            for p in proxies
            if p.id and (isinstance(p, RawXrayConfig) or getattr(p, "is_raw", False))
        ]
        total_count = len(proxy_ids) + len(raw_ids)
        if total_count == 0:
            return

        msg = (
            LanguageManager.tr("scn_msg_del_single_prompt").format(
                remark=proxies[0].remark
            )
            if total_count == 1
            else LanguageManager.tr("scn_msg_del_multi_prompt").format(count=total_count)
        )

        reply = QMessageBox.question(
            self.parent_widget,
            LanguageManager.tr("scn_msg_del_title"),
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.action_running = True
            self.state_changed.emit(True)
            self.worker_action = AsyncTaskWorker(
                self.repository.delete_mixed_many(proxy_ids, raw_ids)
            )
            self.worker_action.finished_signal.connect(self._handle_worker_finish)
            self.worker_action.error_signal.connect(self._handle_worker_error)
            self.worker_action.start()
