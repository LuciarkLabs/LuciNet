import os
import sys
import subprocess
from PySide6.QtWidgets import QMainWindow, QApplication, QSystemTrayIcon
from PySide6.QtGui import QIcon

from gui.main_window_ui import MainWindowUI
from gui.tray_manager import TrayManager
from gui.import_manager import ImportManager

from gui.theme_manager import ThemeManager
from gui.language_manager import LanguageManager
from services.subscription_service import SubscriptionService
from gui.event_bus import event_bus

from gui.tabs.connect.tab_main import ConnectTab
from gui.tabs.archive.tab_main import ArchiveTab
from gui.tabs.scanner.tab_main import ScannerTab
from gui.tabs.rename.tab_main import RenameTab
from gui.tabs.export.tab_main import ExportTab
from gui.tabs.dashboard.tab_main import DashboardTab
from gui.tabs.about.tab_main import AboutTab

class MainWindow(QMainWindow):
    def __init__(self, parser_factory, repository, scan_service):
        super().__init__()
        self.parser_factory = parser_factory
        self.repository = repository
        self.scan_service = scan_service
        self._really_quit = False

        self.setWindowTitle("LuciNet Client")
        self.setMinimumSize(1100, 750)
        self.setWindowIcon(QIcon("assets/icon.png"))

        ThemeManager.apply_theme()

        self.ui = MainWindowUI()
        self.ui.setup_ui(self)

        self.subscription_service = SubscriptionService(
            self.repository, self.parser_factory
        )
        self.connect_tab = ConnectTab(self.repository, self.scan_service)
        self.archive_tab = ArchiveTab(
            self.repository, self.scan_service, self.subscription_service
        )

        self.ui.stacked_widget.addWidget(self.connect_tab)
        self.ui.stacked_widget.addWidget(self.archive_tab)

        self.tray_manager = TrayManager(self)
        self.import_manager = ImportManager(self)

        self._connect_signals()

        self.show_connect_view()
        self._update_theme_button_ui()
        self.retranslate_ui()

        event_bus.request_view_change.connect(self._handle_view_change)
        event_bus.connection_status_changed.connect(
            self.tray_manager.update_tray_status
        )

    def _connect_signals(self):

        self.ui.btn_nav_connect.clicked.connect(self.show_connect_view)
        self.ui.btn_nav_archive.clicked.connect(self.show_archive_view)
        self.ui.btn_quick_dashboard.clicked.connect(self.show_dashboard_window)
        self.ui.btn_quick_scanner.clicked.connect(self.show_scanner_window)
        self.ui.btn_quick_rename.clicked.connect(self.show_rename_window)
        self.ui.btn_quick_about.clicked.connect(self.show_about_window)

        self.ui.btn_lang.clicked.connect(self.toggle_language)
        self.ui.btn_theme.clicked.connect(self.toggle_theme)

        self.ui.action_import_clipboard.triggered.connect(
            self.import_manager.import_from_clipboard
        )
        self.ui.action_import_file.triggered.connect(
            self.import_manager.import_from_file
        )
        self.ui.action_add_manual.triggered.connect(
            self.import_manager.show_manual_config_window
        )

        self.ui.action_export.triggered.connect(self.show_export_window)

    def show_connect_view(self):
        self.ui.stacked_widget.setCurrentWidget(self.connect_tab)

    def show_archive_view(self):
        self.ui.stacked_widget.setCurrentWidget(self.archive_tab)

    def _handle_view_change(self, view_name):
        if view_name == "connect":
            self.show_connect_view()
        elif view_name == "archive":
            self.show_archive_view()

    def show_window(self):
        self.showNormal()
        self.activateWindow()

    def force_quit(self):
        self._really_quit = True
        self.close()
        QApplication.instance().quit()

    def closeEvent(self, event):
        if not self._really_quit:
            event.ignore()
            self.hide()
            self.tray_manager.tray_icon.showMessage(
                LanguageManager.tr("app_title"),
                LanguageManager.tr("tray_msg_minimized"),
                QSystemTrayIcon.MessageIcon.Information,
                1500,
            )
            return

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

        for win_name in [
            "window_export",
            "window_scanner",
            "window_rename",
            "window_dashboard",
            "window_about",
        ]:
            if hasattr(self, win_name):
                getattr(self, win_name).close()

        event.accept()

    def show_export_window(self):
        if not hasattr(self, "window_export"):
            self.window_export = ExportTab(self.repository)
            self.window_export.setWindowTitle("Export")
            self.window_export.resize(500, 400)
            self.window_export.retranslate_ui()
        self.window_export.show()
        self.window_export.activateWindow()

    def show_scanner_window(self):
        if not hasattr(self, "window_scanner"):
            self.window_scanner = ScannerTab(self.repository, self.scan_service)
            self.window_scanner.setWindowTitle("Advanced Scanner")
            self.window_scanner.resize(950, 700)
            self.window_scanner.retranslate_ui()
        self.window_scanner.show()
        self.window_scanner.activateWindow()

    def show_rename_window(self):
        if not hasattr(self, "window_rename"):
            self.window_rename = RenameTab(self.repository)
            self.window_rename.setWindowTitle("Rename & Edit")
            self.window_rename.resize(600, 500)
            self.window_rename.retranslate_ui()
        self.window_rename.show()
        self.window_rename.activateWindow()

    def show_dashboard_window(self):
        if not hasattr(self, "window_dashboard"):
            self.window_dashboard = DashboardTab(self.repository)
            self.window_dashboard.setWindowTitle("Dashboard")
            self.window_dashboard.resize(900, 650)
            self.window_dashboard.retranslate_ui()
        self.window_dashboard.show()
        self.window_dashboard.activateWindow()

    def show_about_window(self):
        if not hasattr(self, "window_about"):
            self.window_about = AboutTab()
            self.window_about.setWindowTitle("About LuciNet")
            self.window_about.resize(500, 400)
            self.window_about.retranslate_ui()
        self.window_about.show()
        self.window_about.activateWindow()

    def toggle_theme(self):
        ThemeManager.toggle_theme()
        self._update_theme_button_ui()

    def _update_theme_button_ui(self):
        if ThemeManager.is_dark:
            self.ui.btn_theme.setText(LanguageManager.tr("btn_light"))
            self.ui.btn_theme.setStyleSheet(
                "QPushButton { background-color: #fbc531; color: #2f3640; border-radius: 6px; padding: 10px; font-weight: bold; font-size: 13px; } QPushButton:hover { background-color: #e1b12c; }"
            )
        else:
            self.ui.btn_theme.setText(LanguageManager.tr("btn_dark"))
            self.ui.btn_theme.setStyleSheet(
                "QPushButton { background-color: #718093; color: white; border-radius: 6px; padding: 10px; font-weight: bold; font-size: 13px; } QPushButton:hover { background-color: #2f3640; }"
            )

    def toggle_language(self):
        LanguageManager.toggle_language()
        self.retranslate_ui()

        windows = [
            self.connect_tab,
            self.archive_tab,
            getattr(self, "window_export", None),
            getattr(self, "window_scanner", None),
            getattr(self, "window_rename", None),
            getattr(self, "window_dashboard", None),
            getattr(self, "window_about", None),
        ]
        for win in windows:
            if win and hasattr(win, "retranslate_ui"):
                win.retranslate_ui()

    def retranslate_ui(self):
        self.ui.app_title.setText(LanguageManager.tr("app_title"))
        self.ui.btn_nav_connect.setText(LanguageManager.tr("tab_connect"))
        self.ui.btn_nav_archive.setText(LanguageManager.tr("tab_archive"))
        self.ui.btn_quick_dashboard.setText(LanguageManager.tr("tab_dashboard"))
        self.ui.btn_quick_scanner.setText(LanguageManager.tr("tab_scanner"))
        self.ui.btn_quick_rename.setText(LanguageManager.tr("tab_rename"))
        self.ui.btn_quick_about.setText(LanguageManager.tr("tab_about"))

        self.ui.menu_servers.setTitle(LanguageManager.tr("menu_servers"))
        self.ui.action_import_clipboard.setText(
            LanguageManager.tr("menu_import_clipboard")
        )
        self.ui.action_import_file.setText(LanguageManager.tr("menu_import_file"))
        self.ui.action_add_manual.setText(LanguageManager.tr("menu_add_manual"))
        self.ui.action_export.setText(LanguageManager.tr("menu_action_export"))

        self._update_theme_button_ui()
        self.tray_manager.retranslate_ui()
