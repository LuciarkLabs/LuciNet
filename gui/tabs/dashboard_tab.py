import re
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QTableView,
    QHeaderView,
    QGridLayout,
    QMenu,
    QApplication,
    QMessageBox,
    QSizePolicy,
    QFrame,
)
from PySide6.QtCore import Qt
from gui.workers import AsyncTaskWorker
from gui.models.proxy_table_model import ProxyTableModel
from gui.language_manager import LanguageManager

def clean_proxy_url(raw_url):
    if not raw_url:
        return ""
    return re.sub(r"[\x00-\x1f\x7f]", "", raw_url).strip()

class DashboardTab(QWidget):
    def __init__(self, repository):
        super().__init__()
        self.repository = repository
        self.current_stats = None
        self._setup_ui()
        self.load_statistics()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header_layout = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; background: transparent;"
        )
        self.btn_refresh = QPushButton()
        self.btn_refresh.setMinimumHeight(35)
        self.btn_refresh.setStyleSheet(
            "background-color: #0097e6; color: white; font-weight: bold; border-radius: 5px; padding: 0 15px;"
        )
        self.btn_refresh.clicked.connect(self.load_statistics)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        cards_layout = QHBoxLayout()

        self.lbl_total_title, self.lbl_total = self._create_stat_card(
            "0", "#00a8ff", cards_layout
        )
        self.lbl_valid_title, self.lbl_valid = self._create_stat_card(
            "0", "#44bd32", cards_layout
        )
        self.lbl_timeout_title, self.lbl_timeout = self._create_stat_card(
            "0", "#e1b12c", cards_layout
        )
        self.lbl_error_title, self.lbl_error = self._create_stat_card(
            "0", "#e84118", cards_layout
        )

        layout.addLayout(cards_layout)

        middle_layout = QHBoxLayout()

        self.protocol_group = QGroupBox()
        self.protocol_container = QWidget()
        self.layout_protocols = QGridLayout(self.protocol_container)
        self.layout_protocols.setContentsMargins(10, 15, 10, 10)
        self.layout_protocols.setSpacing(10)

        pg_layout = QVBoxLayout(self.protocol_group)
        pg_layout.addWidget(self.protocol_container)

        middle_layout.addWidget(self.protocol_group, stretch=1)

        self.network_group = QGroupBox()
        network_layout = QVBoxLayout(self.network_group)
        network_layout.setContentsMargins(10, 15, 10, 10)
        self.lbl_avg_ping = QLabel()
        self.lbl_avg_ping.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #8c7ae6; background: transparent;"
        )
        self.lbl_untested = QLabel()

        network_layout.addStretch()
        network_layout.addWidget(
            self.lbl_avg_ping, alignment=Qt.AlignmentFlag.AlignCenter
        )
        network_layout.addWidget(
            self.lbl_untested, alignment=Qt.AlignmentFlag.AlignCenter
        )
        network_layout.addStretch()
        middle_layout.addWidget(self.network_group, stretch=1)

        layout.addLayout(middle_layout)

        self.top_proxies_group = QGroupBox()
        top_layout = QVBoxLayout(self.top_proxies_group)
        top_layout.setContentsMargins(10, 15, 10, 10)

        self.table_view = QTableView()
        self.top_model = ProxyTableModel([])
        self.table_view.setModel(self.top_model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        cols_to_hide = [0, 5, 6, 7, 8, 10]
        for col in cols_to_hide:
            self.table_view.setColumnHidden(col, True)

        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)

        top_layout.addWidget(self.table_view)
        layout.addWidget(self.top_proxies_group)

        self.retranslate_ui()

    def _create_stat_card(self, value, color, parent_layout):
        card = QFrame()
        card.setStyleSheet(f"border-bottom: 4px solid {color};")
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(15, 20, 15, 20)

        lbl_title = QLabel()
        lbl_title.setStyleSheet(
            "color: #7f8fa6; font-size: 13px; font-weight: bold; border: none; background: transparent;"
        )
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(
            f"color: {color}; font-size: 30px; font-weight: bold; border: none; background: transparent;"
        )
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        parent_layout.addWidget(card)
        return lbl_title, lbl_val

    def show_context_menu(self, pos):
        index = self.table_view.indexAt(pos)
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

        action = menu.exec(self.table_view.viewport().mapToGlobal(pos))

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
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText(LanguageManager.tr("dash_btn_refreshing"))
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
        self.lbl_total.setText(str(stats["total"]))
        self.lbl_valid.setText(str(stats["valid"]))
        self.lbl_timeout.setText(str(stats["timeout"]))
        self.lbl_error.setText(str(stats["error"]))

        while self.layout_protocols.count():
            item = self.layout_protocols.takeAt(0)
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
            self.layout_protocols.addWidget(lbl, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        self.top_model.update_data(stats["top_5"])
        self.btn_refresh.setEnabled(True)
        self.retranslate_ui()

    def retranslate_ui(self):

        self.title_label.setText(LanguageManager.tr("dash_title"))

        if self.btn_refresh.isEnabled():
            self.btn_refresh.setText(LanguageManager.tr("dash_btn_refresh"))
        else:
            self.btn_refresh.setText(LanguageManager.tr("dash_btn_refreshing"))

        self.lbl_total_title.setText(LanguageManager.tr("dash_card_total"))
        self.lbl_valid_title.setText(LanguageManager.tr("dash_card_valid"))
        self.lbl_timeout_title.setText(LanguageManager.tr("dash_card_timeout"))
        self.lbl_error_title.setText(LanguageManager.tr("dash_card_error"))

        self.protocol_group.setTitle(LanguageManager.tr("dash_group_protocols"))
        self.network_group.setTitle(LanguageManager.tr("dash_group_network"))
        self.top_proxies_group.setTitle(LanguageManager.tr("dash_group_top_proxies"))

        if self.current_stats:
            avg = round(self.current_stats["avg_ping"], 1)
            unt = self.current_stats["untested"]
            self.lbl_avg_ping.setText(
                f"{LanguageManager.tr('dash_avg_ping_prefix')} {avg} ms"
            )
            self.lbl_untested.setText(
                f"{LanguageManager.tr('dash_untested_prefix')} {unt}"
            )
        else:
            self.lbl_avg_ping.setText(
                f"{LanguageManager.tr('dash_avg_ping_prefix')} 0 ms"
            )
            self.lbl_untested.setText(f"{LanguageManager.tr('dash_untested_prefix')} 0")
