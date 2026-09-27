
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction, QIcon
from gui.language_manager import LanguageManager


class TrayManager:
    def __init__(self, main_window):
        self.main_window = main_window

        self._last_status = False

        self.tray_icon = QSystemTrayIcon(main_window)
        self.tray_icon.setIcon(QIcon("assets/icon.png"))
        self.tray_icon.setToolTip(LanguageManager.tr("tray_status_disconnected"))

        self.tray_menu = QMenu()

        self.action_show_app = QAction(LanguageManager.tr("tray_open"), main_window)
        self.action_show_app.triggered.connect(self.main_window.show_window)

        self.action_tray_connect = QAction(
            LanguageManager.tr("tray_connect"), main_window
        )
        self.action_tray_connect.triggered.connect(self._tray_connect_clicked)

        self.action_tray_disconnect = QAction(
            LanguageManager.tr("tray_disconnect"), main_window
        )
        self.action_tray_disconnect.triggered.connect(self._tray_disconnect_clicked)
        self.action_tray_disconnect.setVisible(False)

        self.action_quit_app = QAction(LanguageManager.tr("tray_quit"), main_window)
        self.action_quit_app.triggered.connect(self.main_window.force_quit)

        self.tray_menu.addAction(self.action_show_app)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.action_tray_connect)
        self.tray_menu.addAction(self.action_tray_disconnect)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.action_quit_app)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _tray_connect_clicked(self):
        """زمانی که از منوی Tray درخواست اتصال صادر می‌شود"""
        if not self.main_window.connect_tab.selected_proxy:
            self.main_window.show_window()
        self.main_window.connect_tab.toggle_connection()

    def _tray_disconnect_clicked(self):
        """قطع اتصال از منوی سیستم ترِی"""
        self.main_window.connect_tab.toggle_connection()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.main_window.show_window()

    def update_tray_status(self, is_connected):
        """آپدیت دوزبانه بودن نوتیفیکیشن‌ها و دکمه‌های متصل/قطع"""

        if hasattr(self, "_last_status") and self._last_status == is_connected:
            return
        self._last_status = is_connected

        if is_connected:
            self.tray_icon.setToolTip(LanguageManager.tr("tray_status_connected"))
            self.tray_icon.showMessage(
                LanguageManager.tr("app_title"),
                LanguageManager.tr("tray_msg_connected"),
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            self.action_tray_connect.setVisible(False)
            self.action_tray_disconnect.setVisible(True)
        else:
            self.tray_icon.setToolTip(LanguageManager.tr("tray_status_disconnected"))
            self.tray_icon.showMessage(
                LanguageManager.tr("app_title"),
                LanguageManager.tr("tray_msg_disconnected"),
                QSystemTrayIcon.MessageIcon.Warning,
                2000,
            )
            self.action_tray_connect.setVisible(True)
            self.action_tray_disconnect.setVisible(False)

    def retranslate_ui(self):
        """آپدیت آنی متون منوی System Tray با تغییر زبان"""
        self.action_show_app.setText(LanguageManager.tr("tray_open"))
        self.action_tray_connect.setText(LanguageManager.tr("tray_connect"))
        self.action_tray_disconnect.setText(LanguageManager.tr("tray_disconnect"))
        self.action_quit_app.setText(LanguageManager.tr("tray_quit"))

        if (
            getattr(self.main_window.connect_tab, "core_manager", None)
            and self.main_window.connect_tab.core_manager.is_connected
        ):
            self.tray_icon.setToolTip(LanguageManager.tr("tray_status_connected"))
        else:
            self.tray_icon.setToolTip(LanguageManager.tr("tray_status_disconnected"))
