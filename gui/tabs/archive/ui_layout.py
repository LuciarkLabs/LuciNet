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
)
from PySide6.QtCore import Qt

class ArchiveUiLayout:
    def setup_ui(self, parent_widget):
\
\
\

        layout = QVBoxLayout(parent_widget)
        toolbar = QHBoxLayout()

        self.lbl_archive = QLabel()
        toolbar.addWidget(self.lbl_archive)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItem("")
        toolbar.addWidget(self.cmb_filter)

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
        layout.addLayout(toolbar)

        self.filter_group = QGroupBox()
        self.filter_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 30px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                top: 0px;
                padding: 4px 10px;
            }
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
        self.cmb_protocol.addItems(["", "vless", "vmess", "trojan", "ss"])

        filter_layout.addWidget(self.lbl_search)
        filter_layout.addWidget(self.txt_search)
        filter_layout.addWidget(self.lbl_status_filter)
        filter_layout.addWidget(self.cmb_status)
        filter_layout.addWidget(self.lbl_protocol_filter)
        filter_layout.addWidget(self.cmb_protocol)

        layout.addWidget(self.filter_group)

        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        layout.addWidget(self.table_view)

        bottom_layout = QHBoxLayout()

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("font-weight: bold;")
        bottom_layout.addWidget(self.lbl_count)

        bottom_layout.addSpacing(20)

        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet("color: #0097e6; font-weight: bold;")
        self.lbl_status.hide()
        bottom_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        bottom_layout.addWidget(self.progress_bar)

        bottom_layout.addStretch()

        self.btn_refresh = QPushButton()
        bottom_layout.addWidget(self.btn_refresh)

        layout.addLayout(bottom_layout)
