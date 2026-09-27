
from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QHeaderView,
    QLabel,
    QProgressBar,
    QSpinBox,
    QComboBox,
    QLineEdit,
    QGroupBox,
    QCheckBox,
    QRadioButton,
    QButtonGroup,
)
from PySide6.QtCore import Qt


class ScannerUiLayout:
    def setup_ui(self, parent_widget):
        """
        این متد فقط المان‌های بصری تب اسکنر را می‌سازد.
        هیچ‌گونه منطق پردازشی، اتصال به موتور Xray یا دیتابیس در اینجا وجود ندارد.
        """
        layout = QVBoxLayout(parent_widget)
        toolbar = QHBoxLayout()

        archive_toolbar = QHBoxLayout()

        self.lbl_archive = QLabel()
        archive_toolbar.addWidget(self.lbl_archive)

        self.cmb_group = QComboBox()
        self.cmb_group.addItem("")
        self.cmb_group.setMinimumWidth(120)
        archive_toolbar.addWidget(self.cmb_group)

        self.btn_refresh = QPushButton()
        archive_toolbar.addWidget(self.btn_refresh)
        archive_toolbar.addSpacing(10)

        self.btn_load_untested = QPushButton()
        self.btn_load_all = QPushButton()
        archive_toolbar.addWidget(self.btn_load_untested)
        archive_toolbar.addWidget(self.btn_load_all)

        archive_toolbar.addSpacing(25)

        probe_radio_style = """
            QRadioButton {
                spacing: 6px;
                font-weight: bold;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 9px;
                border: 2px solid #718093;
                background-color: transparent;
            }
            QRadioButton::indicator:hover {
                border-color: #00a8ff;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #00a8ff;
                background-color: qradialgradient(
                    cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5,
                    stop: 0 #00a8ff, stop: 0.50 #00a8ff, stop: 0.55 transparent, stop: 1 transparent
                );
            }
            QRadioButton::indicator:disabled {
                border-color: #576574;
                background-color: transparent;
            }
            QRadioButton::indicator:checked:disabled {
                border-color: #576574;
                background-color: qradialgradient(
                    cx: 0.5, cy: 0.5, radius: 0.5, fx: 0.5, fy: 0.5,
                    stop: 0 #576574, stop: 0.50 #576574, stop: 0.55 transparent, stop: 1 transparent
                );
            }
            QRadioButton:disabled {
                color: #718093;
            }
        """

        self.probe_group = QButtonGroup(parent_widget)
        self.rb_probe_http = QRadioButton("HTTP 80")
        self.rb_probe_http.setChecked(True)
        self.rb_probe_http.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rb_probe_http.setStyleSheet(probe_radio_style)
        self.probe_group.addButton(self.rb_probe_http)
        archive_toolbar.addWidget(self.rb_probe_http)

        archive_toolbar.addSpacing(10)

        self.rb_probe_https = QRadioButton("HTTPS 443")
        self.rb_probe_https.setChecked(False)
        self.rb_probe_https.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rb_probe_https.setStyleSheet(probe_radio_style)
        self.probe_group.addButton(self.rb_probe_https)
        archive_toolbar.addWidget(self.rb_probe_https)

        archive_toolbar.addStretch()
        layout.addLayout(archive_toolbar)

        scan_toolbar = QHBoxLayout()

        safe_spinbox_style = """
            QSpinBox { padding-right: 25px; }
            QSpinBox::up-button, QSpinBox::down-button { width: 20px; }
        """

        self.spin_concurrent = QSpinBox()
        self.spin_concurrent.setRange(1, 1000)
        self.spin_concurrent.setValue(50)
        self.spin_concurrent.setMinimumWidth(90)
        self.spin_concurrent.setFixedHeight(32)
        self.spin_concurrent.setStyleSheet(safe_spinbox_style)

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(1, 60)
        self.spin_timeout.setValue(15)
        self.spin_timeout.setMinimumWidth(90)
        self.spin_timeout.setFixedHeight(32)
        self.spin_timeout.setStyleSheet(safe_spinbox_style)

        self.lbl_concurrent = QLabel()
        self.lbl_timeout = QLabel()

        self.lbl_speed_size = QLabel()
        self.cmb_speed_size = QComboBox()
        self.cmb_speed_size.setFixedHeight(32)

        scan_toolbar.addWidget(self.lbl_concurrent)
        scan_toolbar.addWidget(self.spin_concurrent)
        scan_toolbar.addSpacing(10)

        scan_toolbar.addWidget(self.lbl_timeout)
        scan_toolbar.addWidget(self.spin_timeout)
        scan_toolbar.addSpacing(10)

        scan_toolbar.addWidget(self.lbl_speed_size)
        scan_toolbar.addWidget(self.cmb_speed_size)
        scan_toolbar.addSpacing(15)

        self.chk_deep_scan = QCheckBox()
        self.chk_deep_scan.setChecked(False)
        self.chk_deep_scan.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_toolbar.addWidget(self.chk_deep_scan)

        scan_toolbar.addStretch()

        self.btn_scan_selected = QPushButton()
        self.btn_scan_selected.setStyleSheet(
            "background-color: #fbc531; color: #2f3640; font-weight: bold;"
        )
        self.btn_scan_selected.setEnabled(False)

        self.btn_speed_valid = QPushButton()
        self.btn_speed_valid.setStyleSheet(
            "background-color: #00a8ff; color: white; font-weight: bold;"
        )
        self.btn_speed_valid.setEnabled(False)

        self.btn_start = QPushButton()
        self.btn_start.setStyleSheet(
            "background-color: #44bd32; color: white; font-weight: bold;"
        )
        self.btn_start.setEnabled(False)

        self.btn_stop = QPushButton()
        self.btn_stop.setStyleSheet(
            "background-color: #e84118; color: white; font-weight: bold;"
        )
        self.btn_stop.setEnabled(False)

        scan_toolbar.addWidget(self.btn_scan_selected)
        scan_toolbar.addWidget(self.btn_speed_valid)
        scan_toolbar.addWidget(self.btn_start)
        scan_toolbar.addWidget(self.btn_stop)

        layout.addLayout(scan_toolbar)

        progress_layout = QHBoxLayout()
        self.lbl_status = QLabel()
        self.lbl_status.setMinimumWidth(250)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.lbl_status)
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)

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

        layout.addWidget(self.filter_group)

        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.table_view)
