import os
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

class AboutUiLayout:
    def setup_ui(self, parent_widget):
\
\
\

        layout = QVBoxLayout(parent_widget)
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

        self.lbl_version = QLabel("v1.2.0")
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
            "background-color: #2f3640; color: white; font-weight: bold; border-radius: 25px; font-size: 14px;"
            "min-width: 140px; max-width: 140px; min-height: 39px; max-height: 39px;"
        )

        self.btn_telegram = QPushButton()
        self.btn_telegram.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_telegram.setStyleSheet(
            "background-color: #00a8ff; color: white; font-weight: bold; border-radius: 25px; font-size: 14px;"
            "min-width: 140px; max-width: 140px; min-height: 39px; max-height: 39px;"
        )

        self.btn_update = QPushButton()
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.setStyleSheet(
            "background-color: #44bd32; color: white; font-weight: bold; border-radius: 25px; font-size: 14px;"
            "min-width: 145px; max-width: 145px; min-height: 39px; max-height: 39px;"
        )

        row1_layout = QHBoxLayout()
        row1_layout.addStretch()
        row1_layout.addWidget(self.btn_telegram)
        row1_layout.addWidget(self.btn_github)
        row1_layout.addStretch()

        row2_layout = QHBoxLayout()
        row2_layout.addStretch()
        row2_layout.addWidget(self.btn_update)
        row2_layout.addStretch()

        layout.addLayout(row1_layout)
        layout.addSpacing(5)
        layout.addLayout(row2_layout)
