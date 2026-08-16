import re
from PySide6.QtWidgets import (
    QWidget,
    QMenu,
    QApplication,
    QMessageBox,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from gui.workers import AsyncTaskWorker
from gui.models.proxy_table_model import ProxyTableModel
from gui.language_manager import LanguageManager
from .ui_layout import DashboardUiLayout
from gui.event_bus import event_bus

def clean_proxy_url(raw_url):

    if not raw_url:
        return ""
    return re.sub(r"[\x00-\x1f\x7f]", "", raw_url).strip()

class DashboardTab(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.current_stats = None
        self.is_db_locked = False

        self.ui = DashboardUiLayout()
        self.ui.setup_ui(self)

        self.top_model = ProxyTableModel([])
        self.ui.table_view.setModel(self.top_model)

        cols_to_hide = [0, 5, 6, 7, 8, 10]
        for col in cols_to_hide:
            self.ui.table_view.setColumnHidden(col, True)

        self.ui.btn_refresh.clicked.connect(self.load_statistics)
        self.ui.table_view.customContextMenuRequested.connect(self.show_context_menu)

        event_bus.data_changed.connect(self.load_statistics)
        event_bus.scan_lock_changed.connect(
            self.on_scan_lock_changed
        )

        self.load_statistics()
        self.retranslate_ui()

    def on_scan_lock_changed(self, is_locked, group_name):

        self.is_db_locked = is_locked
        self.ui.btn_refresh.setEnabled(not is_locked)

    def show_context_menu(self, pos):
        index = self.ui.table_view.indexAt(pos)
        menu = QMenu(self)

        action_copy = None
        if index.isValid():
            action_copy = menu.addAction(LanguageManager.tr("dash_menu_copy_single"))

        action_copy_all = None
        if self.top_model.proxies:
            txt = LanguageManager.tr("dash_menu_copy_all").format(
                count=len(self.top_model.proxies)
            )
            action_copy_all = menu.addAction(txt)

        if menu.isEmpty():
            return

        action = menu.exec(self.ui.table_view.viewport().mapToGlobal(pos))

        if action_copy and action == action_copy:
            proxy = self.top_model.proxies[index.row()]
            clean_url = clean_proxy_url(proxy.raw_url)
            QApplication.clipboard().clear()
            QApplication.clipboard().setText(clean_url)
            QMessageBox.information(
                self,
                LanguageManager.tr("dash_msg_copy_single_title"),
                LanguageManager.tr("dash_msg_copy_single_body"),
            )

        elif action_copy_all and action == action_copy_all:
            urls = [
                clean_proxy_url(p.raw_url) for p in self.top_model.proxies if p.raw_url
            ]
            urls = [u for u in urls if u]
            text_to_copy = "\r\n".join(urls)

            QApplication.clipboard().clear()
            QApplication.clipboard().setText(text_to_copy)
            QMessageBox.information(
                self,
                LanguageManager.tr("dash_msg_copy_all_title"),
                LanguageManager.tr("dash_msg_copy_all_body").format(count=len(urls)),
            )

    def load_statistics(self):
        if self.is_db_locked:
            return
        self.ui.btn_refresh.setEnabled(False)
        self.ui.btn_refresh.setText(LanguageManager.tr("dash_btn_refreshing"))
        self.worker = AsyncTaskWorker(self._calculate_stats_async())
        self.worker.finished_signal.connect(self._on_stats_loaded)
        self.worker.start()

    async def _calculate_stats_async(self):
        proxies = await self.repository.get_all()

        total = len(proxies)
        valid = sum(1 for p in proxies if p.status == "Valid")
        timeout = sum(1 for p in proxies if p.status == "Timeout")
        error = sum(1 for p in proxies if p.status in ("Error", "Invalid"))
        untested = sum(1 for p in proxies if p.status == "Untested")

        protocols = {}
        valid_proxies = []

        for p in proxies:
            pr = p.protocol.upper() if p.protocol else "UNKNOWN"
            protocols[pr] = protocols.get(pr, 0) + 1
            if p.status == "Valid" and p.ping > 0:
                valid_proxies.append(p)

        avg_ping = (
            sum(p.ping for p in valid_proxies) / len(valid_proxies)
            if valid_proxies
            else 0
        )
        top_5 = sorted(valid_proxies, key=lambda x: x.ping)[:5]

        return {
            "total": total,
            "valid": valid,
            "timeout": timeout,
            "error": error,
            "untested": untested,
            "protocols": protocols,
            "avg_ping": avg_ping,
            "top_5": top_5,
        }

    def _on_stats_loaded(self, stats):
        self.current_stats = stats

        self.ui.lbl_total.setText(str(stats["total"]))
        self.ui.lbl_valid.setText(str(stats["valid"]))
        self.ui.lbl_timeout.setText(str(stats["timeout"]))
        self.ui.lbl_error.setText(str(stats["error"]))

        while self.ui.layout_protocols.count():
            item = self.ui.layout_protocols.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        row, col = 0, 0
        for proto, count in stats["protocols"].items():
            lbl = QLabel(f"{proto}\n{count}")
            lbl.setStyleSheet(
                "background-color: rgba(130, 130, 130, 0.2); border-radius: 6px; font-weight: bold; font-size: 14px; border: none;"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self.ui.layout_protocols.addWidget(lbl, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        self.top_model.update_data(stats["top_5"])
        self.ui.btn_refresh.setEnabled(True)
        self.retranslate_ui()

    def retranslate_ui(self):
        self.ui.title_label.setText(LanguageManager.tr("dash_title"))

        if self.ui.btn_refresh.isEnabled():
            self.ui.btn_refresh.setText(LanguageManager.tr("dash_btn_refresh"))
        else:
            self.ui.btn_refresh.setText(LanguageManager.tr("dash_btn_refreshing"))

        self.ui.lbl_total_title.setText(LanguageManager.tr("dash_card_total"))
        self.ui.lbl_valid_title.setText(LanguageManager.tr("dash_card_valid"))
        self.ui.lbl_timeout_title.setText(LanguageManager.tr("dash_card_timeout"))
        self.ui.lbl_error_title.setText(LanguageManager.tr("dash_card_error"))

        self.ui.protocol_group.setTitle(LanguageManager.tr("dash_group_protocols"))
        self.ui.network_group.setTitle(LanguageManager.tr("dash_group_network"))
        self.ui.top_proxies_group.setTitle(LanguageManager.tr("dash_group_top_proxies"))

        if self.current_stats:
            avg = round(self.current_stats["avg_ping"], 1)
            unt = self.current_stats["untested"]
            self.ui.lbl_avg_ping.setText(
                f"{LanguageManager.tr('dash_avg_ping_prefix')} {avg} ms"
            )
            self.ui.lbl_untested.setText(
                f"{LanguageManager.tr('dash_untested_prefix')} {unt}"
            )
        else:
            self.ui.lbl_avg_ping.setText(
                f"{LanguageManager.tr('dash_avg_ping_prefix')} 0 ms"
            )
            self.ui.lbl_untested.setText(
                f"{LanguageManager.tr('dash_untested_prefix')} 0"
            )
