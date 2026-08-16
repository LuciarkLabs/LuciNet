from PySide6.QtWidgets import (
    QVBoxLayout,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QComboBox,
    QGroupBox,
)

class ExportUiLayout:
    def setup_ui(self, parent_widget):
\
\
\

        layout = QVBoxLayout(parent_widget)

        self.settings_group = QGroupBox()
        settings_layout = QVBoxLayout(self.settings_group)

        group_layout = QHBoxLayout()

        self.lbl_archive = QLabel()
        group_layout.addWidget(self.lbl_archive)

        self.cmb_group = QComboBox()
        self.cmb_group.addItem("", "")
        self.cmb_group.setMinimumWidth(250)
        group_layout.addWidget(self.cmb_group)

        self.btn_refresh_groups = QPushButton()
        group_layout.addWidget(self.btn_refresh_groups)
        group_layout.addStretch()

        settings_layout.addLayout(group_layout)

        self.lbl_info = QLabel()
        self.lbl_info.setStyleSheet("color: #7f8fa6; margin-top: 10px;")
        settings_layout.addWidget(self.lbl_info)

        layout.addWidget(self.settings_group)

        btn_layout = QHBoxLayout()

        self.btn_export_all = QPushButton()
        self.btn_export_all.setMinimumHeight(45)
        self.btn_export_all.setStyleSheet(
            "background-color: #0097e6; color: white; font-weight: bold; border-radius: 5px; padding: 0 20px;"
        )

        self.btn_export_valid = QPushButton()
        self.btn_export_valid.setMinimumHeight(45)
        self.btn_export_valid.setStyleSheet(
            "background-color: #44bd32; color: white; font-weight: bold; border-radius: 5px; padding: 0 20px;"
        )

        btn_layout.addWidget(self.btn_export_all)
        btn_layout.addWidget(self.btn_export_valid)
        layout.addLayout(btn_layout)
        layout.addStretch()
