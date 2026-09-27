from domain.models.raw_config import RawXrayConfig
from domain.models.proxy import ProxyConfig
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMenu, QMessageBox, QApplication, QInputDialog
from gui.widgets.qr_dialog import QRDialog
from gui.language_manager import LanguageManager


class ContextMenuHandler(QObject):
    def __init__(self, parent_widget, tools_manager, table_view, model, proxy_model):
        super().__init__()
        self.parent_widget = parent_widget
        self.tools_manager = tools_manager

        self.table_view = table_view
        self.model = model
        self.proxy_model = proxy_model

    def show_context_menu(self, pos, available_groups, is_db_locked):
        """ساخت و نمایش منوی کلیک‌راست"""
        if is_db_locked or self.tools_manager.is_running:
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

        action_copy = None
        action_qr = None
        if len(selected_proxies) == 1:
            action_copy = menu.addAction(LanguageManager.tr("arc_ctx_copy"))
            if isinstance(proxy, ProxyConfig):
                action_qr = menu.addAction(LanguageManager.tr("arc_ctx_qr"))

        menu.addSeparator()
        action_move = menu.addAction(
            LanguageManager.tr("arc_ctx_move").format(count=len(selected_proxies))
        )
        action_delete = menu.addAction(
            LanguageManager.tr("arc_ctx_delete").format(count=len(selected_proxies))
        )

        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))

        if action_copy and action == action_copy:
            self._copy_to_clipboard(proxy)
        elif action_qr and action == action_qr:
            self._show_qr_dialog(proxy)
        elif action == action_move:
            self._request_move(selected_proxies, available_groups)
        elif action == action_delete:
            self._request_delete(selected_proxies)

    def _copy_to_clipboard(self, proxy):
        text_to_copy = ""
        if isinstance(proxy, RawXrayConfig):
            text_to_copy = proxy.raw_payload
        elif isinstance(proxy, ProxyConfig):
            text_to_copy = proxy.raw_url
        else:
            QMessageBox.warning(self.parent_widget, "Error", "Unknown object type for copy.")
            return

        QApplication.clipboard().setText(text_to_copy)
        QMessageBox.information(
            self.parent_widget,
            LanguageManager.tr("arc_msg_copied_title"),
            LanguageManager.tr("arc_msg_copied_body"),
        )

    def _show_qr_dialog(self, proxy):
        dialog = QRDialog(proxy.remark or "Config", proxy.raw_url, self.parent_widget)
        dialog.exec()

    def _request_move(self, proxies, available_groups):
        """دریافت گروه مقصد از کاربر و ارجاع آن به ToolsManager"""
        proxy_ids = [p.id for p in proxies if p.id and not isinstance(p, RawXrayConfig)]
        raw_ids = [p.id for p in proxies if p.id and isinstance(p, RawXrayConfig)]
        
        if not proxy_ids and not raw_ids:
            return

        groups = [g for g in available_groups if g]
        if "Default" not in groups:
            groups.insert(0, "Default")

        msg = LanguageManager.tr("arc_msg_move_prompt").format(count=len(proxy_ids) + len(raw_ids))

        new_group, ok = QInputDialog.getItem(
            self.parent_widget,
            LanguageManager.tr("arc_msg_move_title"),
            msg,
            groups,
            0,
            True,
        )

        if ok and new_group.strip():
            self.tools_manager.execute_move(proxy_ids, raw_ids, new_group.strip())

    def _request_delete(self, proxies):
        """تاییدیه حذف از کاربر و ارجاع آن به ToolsManager"""
        proxy_ids = [p.id for p in proxies if p.id and not isinstance(p, RawXrayConfig)]
        raw_ids = [p.id for p in proxies if p.id and isinstance(p, RawXrayConfig)]
        
        if not proxy_ids and not raw_ids:
            return

        msg = LanguageManager.tr("arc_msg_del_sel_body").format(count=len(proxy_ids) + len(raw_ids))

        reply = QMessageBox.question(
            self.parent_widget,
            LanguageManager.tr("arc_msg_delete_title"),
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.tools_manager.execute_delete(proxy_ids, raw_ids, action_type="delete_selected")
