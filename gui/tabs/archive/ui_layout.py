
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QLabel,
    QComboBox,
    QMenu,
    QLineEdit,
    QGroupBox,
    QProgressBar,
    QSplitter,
    QScrollArea,
    QFrame,
    QWidget,
    QCheckBox,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt


class ArchiveUiLayout:
    def setup_ui(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()

        self.btn_new_group = QPushButton()
        self.btn_new_group.setStyleSheet("color: #44bd32; font-weight: bold;")
        toolbar.addWidget(self.btn_new_group)

        self.btn_rename_group = QPushButton()
        self.btn_delete_group = QPushButton()
        self.btn_delete_group.setStyleSheet("color: #e84118; font-weight: bold;")

        toolbar.addWidget(self.btn_rename_group)
        toolbar.addWidget(self.btn_delete_group)

        self.btn_tools = QPushButton()
        self.btn_tools.setStyleSheet("font-weight: bold;")

        self.tools_menu = QMenu(parent_widget)
        self.action_move = self.tools_menu.addAction("")
        self.tools_menu.addSeparator()
        self.action_dedup = self.tools_menu.addAction("")
        self.tools_menu.addSeparator()
        self.action_del_inv = self.tools_menu.addAction("")
        self.action_del_tout = self.tools_menu.addAction("")

        self.btn_tools.setMenu(self.tools_menu)
        toolbar.addWidget(self.btn_tools)

        toolbar.addStretch()

        self.btn_quick_connect = QPushButton("⚡ Connect")
        self.btn_quick_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_connect.setStyleSheet("""
            QPushButton {
                background-color: #eb3b5a; /* قرمز به نشانه قطع بودن */
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 18px;
            }
            QPushButton:hover { background-color: #fc5c65; }
        """)
        self.btn_quick_connect.setToolTip(
            "با کلیک روی این دکمه فوراً به کانفیگ انتخاب‌شده متصل شوید"
        )
        toolbar.addWidget(self.btn_quick_connect)

        layout.addLayout(toolbar)

        self.sub_layout = QHBoxLayout()
        self.btn_manage_subs = QPushButton()
        self.btn_update_current_sub = QPushButton()
        self.btn_update_all_subs = QPushButton()

        self.btn_update_current_sub.setEnabled(False)

        self.sub_layout.addWidget(self.btn_manage_subs)
        self.sub_layout.addWidget(self.btn_update_current_sub)
        self.sub_layout.addWidget(self.btn_update_all_subs)
        self.sub_layout.addStretch()

        layout.addLayout(self.sub_layout)

        self.scroll_groups = QScrollArea()
        self.scroll_groups.setWidgetResizable(True)
        self.scroll_groups.setFixedHeight(60)
        self.scroll_groups.setFrameShape(QFrame.NoFrame)
        self.scroll_groups.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.groups_widget = QWidget()
        self.groups_layout = QHBoxLayout(self.groups_widget)
        self.groups_layout.setAlignment(Qt.AlignLeft)
        self.groups_layout.setContentsMargins(5, 5, 5, 5)
        self.groups_layout.setSpacing(10)

        self.scroll_groups.setWidget(self.groups_widget)
        layout.addWidget(self.scroll_groups)

        self.splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.splitter, stretch=1)

        self.table_container = QWidget()
        table_layout = QVBoxLayout(self.table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.filter_group = QGroupBox()
        self.filter_group.setStyleSheet("""
            QGroupBox { font-weight: bold; margin-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; top: 0px; padding: 4px 10px; }
        """)

        filter_layout = QHBoxLayout(self.filter_group)
        self.lbl_search = QLabel()
        self.txt_search = QLineEdit()

        self.lbl_status_filter = QLabel()
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(
            ["", "Valid", "Invalid", "Timeout", "Error", "Untested"]
        )

        self.lbl_protocol_filter = QLabel()
        self.cmb_protocol = QComboBox()
        self.cmb_protocol.addItems(["", "vless", "vmess", "trojan", "ss", "RAW JSON"])

        self.lbl_ip_filter = QLabel()
        self.cmb_ip_filter = QComboBox()
        self.cmb_ip_filter.addItems(["", "IPv4", "IPv6", "Domain"])

        filter_layout.addWidget(self.lbl_search)
        filter_layout.addWidget(self.txt_search)
        filter_layout.addWidget(self.lbl_status_filter)
        filter_layout.addWidget(self.cmb_status)
        filter_layout.addWidget(self.lbl_protocol_filter)
        filter_layout.addWidget(self.cmb_protocol)

        filter_layout.addWidget(self.lbl_ip_filter)
        filter_layout.addWidget(self.cmb_ip_filter)

        table_layout.addWidget(self.filter_group)

        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        table_layout.addWidget(self.table_view)
        self.splitter.addWidget(self.table_container)

        self.console_container = QWidget()
        console_layout = QVBoxLayout(self.console_container)
        console_layout.setContentsMargins(0, 0, 0, 0)

        console_toolbar = QHBoxLayout()
        self.btn_clear_log = QPushButton()
        self.chk_auto_scroll = QCheckBox()
        self.chk_auto_scroll.setChecked(True)

        console_toolbar.addWidget(self.btn_clear_log)
        console_toolbar.addWidget(self.chk_auto_scroll)
        console_toolbar.addStretch()
        console_layout.addLayout(console_toolbar)

        self.txt_console = QPlainTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e; 
                color: #00ff00; 
                font-family: Consolas, 'Courier New', monospace; 
                font-size: 13px;
                padding: 5px;
                border-radius: 4px;
            }
        """)
        console_layout.addWidget(self.txt_console)

        self.splitter.addWidget(self.console_container)
        self.splitter.setSizes([700, 300])

        bottom_layout = QHBoxLayout()

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("font-weight: bold;")
        bottom_layout.addWidget(self.lbl_count)
        bottom_layout.addSpacing(15)

        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet("color: #0097e6; font-weight: bold;")
        self.lbl_status.hide()
        bottom_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        bottom_layout.addWidget(self.progress_bar)

        bottom_layout.addStretch()

        self.btn_toggle_console = QPushButton()
        self.btn_toggle_console.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_console.setCheckable(True)
        self.btn_toggle_console.setChecked(True)
        self.btn_toggle_console.setStyleSheet(
            "font-weight: bold; color: #00a8ff; border: 1px solid #00a8ff; padding: 4px 10px; border-radius: 4px;"
        )
        bottom_layout.addWidget(self.btn_toggle_console)

        bottom_layout.addSpacing(10)

        self.btn_refresh = QPushButton()
        bottom_layout.addWidget(self.btn_refresh)

        layout.addLayout(bottom_layout)
