import os
import sys
import subprocess
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt
from gui.tabs.input_tab import InputTab
from gui.tabs.archive_tab import ArchiveTab
from gui.tabs.scanner_tab import ScannerTab
from gui.tabs.rename_tab import RenameTab
from gui.tabs.export_tab import ExportTab
from gui.tabs.dashboard_tab import DashboardTab
from gui.tabs.about_tab import AboutTab
from gui.theme_manager import ThemeManager
from gui.language_manager import LanguageManager

class MainWindow(QMainWindow):
    def __init__(self, parser_factory, repository, scan_service):
        super().__init__()
        self.setWindowTitle("LuciNet")
        self.setMinimumSize(1050, 750)

        ThemeManager.apply_theme()

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        top_bar = QHBoxLayout()

        self.app_title = QLabel()
        self.app_title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #0097e6; border: none; background: transparent;"
        )

        self.btn_theme = QPushButton()
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)

        self.btn_lang = QPushButton("🌐 English / فارسی")
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setStyleSheet("background-color: #8c7ae6; color: white;")
        self.btn_lang.clicked.connect(self.toggle_language)

        top_bar.addWidget(self.app_title)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_lang)
        top_bar.addWidget(self.btn_theme)

        main_layout.addLayout(top_bar)

        self.tabs = QTabWidget()

        self.dashboard_tab = DashboardTab(repository)
        self.input_tab = InputTab(parser_factory, repository)
        self.archive_tab = ArchiveTab(repository, scan_service)
        self.scanner_tab = ScannerTab(repository, scan_service)
        self.rename_tab = RenameTab(repository)
        self.export_tab = ExportTab(repository)
        self.about_tab = AboutTab()

        self.tabs.addTab(self.dashboard_tab, "")
        self.tabs.addTab(self.input_tab, "")
        self.tabs.addTab(self.archive_tab, "")
        self.tabs.addTab(self.scanner_tab, "")
        self.tabs.addTab(self.rename_tab, "")
        self.tabs.addTab(self.export_tab, "")
        self.tabs.addTab(self.about_tab, "")

        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central_widget)

        self._update_theme_button_ui()
        self.retranslate_ui()

    def toggle_theme(self):
        ThemeManager.toggle_theme()
        self._update_theme_button_ui()

    def _update_theme_button_ui(self):

        if ThemeManager.is_dark:
            self.btn_theme.setText(LanguageManager.tr("btn_light"))
            self.btn_theme.setStyleSheet("background-color: #f1c40f; color: #2f3640;")
        else:
            self.btn_theme.setText(LanguageManager.tr("btn_dark"))
            self.btn_theme.setStyleSheet("background-color: #2f3640; color: white;")

    def toggle_language(self):
        LanguageManager.toggle_language()
        self.retranslate_ui()

        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "retranslate_ui"):
                tab.retranslate_ui()

    def retranslate_ui(self):

        self.app_title.setText(LanguageManager.tr("app_title"))
        self.tabs.setTabText(0, LanguageManager.tr("tab_dashboard"))
        self.tabs.setTabText(1, LanguageManager.tr("tab_input"))
        self.tabs.setTabText(2, LanguageManager.tr("tab_archive"))
        self.tabs.setTabText(3, LanguageManager.tr("tab_scanner"))
        self.tabs.setTabText(4, LanguageManager.tr("tab_rename"))
        self.tabs.setTabText(5, LanguageManager.tr("tab_export"))
        self.tabs.setTabText(
            6, LanguageManager.tr("tab_about")
        )
        self._update_theme_button_ui()

    def closeEvent(self, event):

        try:
            cflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.Popen(
                ["taskkill", "/F", "/IM", "xray.exe", "/T"],
                creationflags=cflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

        try:
            self.scan_service.cancel()
        except Exception:
            pass

        event.accept()
