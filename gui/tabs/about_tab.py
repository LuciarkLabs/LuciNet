import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from gui.language_manager import LanguageManager

class AboutTab(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.retranslate_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_logo = QLabel()
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_path_png = "assets/icon.png"
        logo_path_ico = "assets/icon.ico"

        if os.path.exists(logo_path_png):
            pixmap = QPixmap(logo_path_png).scaled(
                128,
                128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_logo.setPixmap(pixmap)
        elif os.path.exists(logo_path_ico):
            pixmap = QPixmap(logo_path_ico).scaled(
                128,
                128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_logo.setPixmap(pixmap)
        else:

            self.lbl_logo.setText("🚀")
            self.lbl_logo.setStyleSheet("font-size: 80px; background: transparent;")

        layout.addWidget(self.lbl_logo)

        self.lbl_title = QLabel("LuciNet")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet(
            "font-size: 26px; font-weight: bold; color: #0097e6; margin-top: 10px; background: transparent;"
        )
        layout.addWidget(self.lbl_title)

        self.lbl_brand = QLabel("Developed by LuciarkLabs")
        self.lbl_brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_brand.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #8c7ae6; background: transparent;"
        )
        layout.addWidget(self.lbl_brand)

        self.lbl_version = QLabel("v1.1.0")
        self.lbl_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_version.setStyleSheet(
            "font-size: 13px; color: #7f8fa6; margin-bottom: 25px; background: transparent;"
        )
        layout.addWidget(self.lbl_version)

        self.lbl_desc = QLabel()
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet(
            "font-size: 14px; line-height: 1.6; background: transparent;"
        )
        self.lbl_desc.setMaximumWidth(650)

        desc_layout = QHBoxLayout()
        desc_layout.addStretch()
        desc_layout.addWidget(self.lbl_desc)
        desc_layout.addStretch()
        layout.addLayout(desc_layout)

        layout.addSpacing(35)

        self.btn_github = QPushButton()
        self.btn_github.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_github.setStyleSheet(
            "background-color: #2f3640; color: white; font-weight: bold; border-radius: 8px; padding: 12px 35px; font-size: 14px;"
        )
        self.btn_github.clicked.connect(self.open_github)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_github)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def retranslate_ui(self):

        self.lbl_desc.setText(LanguageManager.tr("abt_desc"))
        self.btn_github.setText(LanguageManager.tr("abt_btn_github"))

    def open_github(self):

        QDesktopServices.openUrl(QUrl("https://github.com/LuciarkLabs/LuciNet"))
