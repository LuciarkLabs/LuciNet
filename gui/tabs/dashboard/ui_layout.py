from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QTableView,
    QHeaderView,
    QGridLayout,
    QWidget,
    QFrame,
)
from PySide6.QtCore import Qt

class DashboardUiLayout:
    def setup_ui(self, parent_widget):
\
\
\

        layout = QVBoxLayout(parent_widget)

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

        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        top_layout.addWidget(self.table_view)
        layout.addWidget(self.top_proxies_group)

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
