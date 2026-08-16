from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QSizePolicy,
)

class RenameUiLayout:
    def setup_ui(self, parent_widget):
\
\
\

        layout = QVBoxLayout(parent_widget)

        self.target_group = QGroupBox()
        target_layout = QHBoxLayout(self.target_group)

        self.cmb_archive = QComboBox()
        self.cmb_archive.addItem(
            "", "ALL_ARCHIVES"
        )
        self.cmb_archive.setMinimumWidth(150)

        self.cmb_status = QComboBox()
        self.cmb_status.setMinimumWidth(135)
        self.cmb_status.setMaximumWidth(135)
        self.cmb_status.setMinimumHeight(35)
        self.cmb_status.addItem("", "valid")
        self.cmb_status.addItem("", "all")

        self.btn_refresh_groups = QPushButton()
        self.btn_refresh_groups.setMinimumWidth(120)

        self.lbl_archive = QLabel()
        self.lbl_status = QLabel()

        target_layout.addWidget(self.lbl_archive)
        target_layout.addWidget(self.cmb_archive)
        target_layout.addWidget(self.btn_refresh_groups)
        target_layout.addSpacing(20)
        target_layout.addWidget(self.lbl_status)
        target_layout.addWidget(self.cmb_status)
        target_layout.addStretch()
        layout.addWidget(self.target_group)

        self.settings_group = QGroupBox()
        form_layout = QFormLayout(self.settings_group)

        self.chk_clear_old = QCheckBox()
        self.chk_clear_old.setStyleSheet("color: #e84118; font-weight: bold;")
        self.lbl_clear = QLabel()
        form_layout.addRow(self.lbl_clear, self.chk_clear_old)

        self.txt_prefix = QLineEdit()
        self.lbl_prefix = QLabel()
        form_layout.addRow(self.lbl_prefix, self.txt_prefix)

        self.txt_suffix = QLineEdit()
        self.lbl_suffix = QLabel()
        form_layout.addRow(self.lbl_suffix, self.txt_suffix)

        emoji_layout = QHBoxLayout()
        self.cmb_emoji = QComboBox()

        emoji_options = [
            "none",
            "random_food",
            "random_animal",
            "🔥",
            "✅",
            "🚀",
            "⚡",
            "👑",
            "⭐",
            "💎",
        ]
        for opt in emoji_options:
            self.cmb_emoji.addItem("", opt)

        self.cmb_emoji_pos = QComboBox()
        self.cmb_emoji_pos.addItem("", "start")
        self.cmb_emoji_pos.addItem("", "end")

        emoji_layout.addWidget(self.cmb_emoji)
        emoji_layout.addWidget(self.cmb_emoji_pos)

        self.lbl_emoji = QLabel()
        form_layout.addRow(self.lbl_emoji, emoji_layout)

        self.chk_number = QCheckBox()
        self.lbl_index = QLabel()
        form_layout.addRow(self.lbl_index, self.chk_number)
        layout.addWidget(self.settings_group)

        self.btn_apply = QPushButton()
        self.btn_apply.setMinimumHeight(45)
        self.btn_apply.setStyleSheet(
            "background-color: #8c7ae6; color: white; font-weight: bold; border-radius: 5px; font-size: 14px;"
        )

        layout.addStretch()
        layout.addWidget(self.btn_apply)
