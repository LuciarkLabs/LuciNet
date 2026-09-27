
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt


class MainWindowUI:
    def setup_ui(self, main_window):
        """ساخت و چینش تمام المان‌های گرافیکی پنجره اصلی"""

        self._create_menu_bar(main_window)

        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setObjectName("leftSidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 25, 15, 20)
        sidebar_layout.setSpacing(8)

        self.app_title = QLabel()
        self.app_title.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #00a8ff; border: none; background: transparent; margin-bottom: 20px;"
        )
        sidebar_layout.addWidget(self.app_title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_nav_connect = self._create_sidebar_btn()
        self.btn_nav_archive = self._create_sidebar_btn()
        sidebar_layout.addWidget(self.btn_nav_connect)
        sidebar_layout.addWidget(self.btn_nav_archive)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("sidebarSeparator")
        sidebar_layout.addWidget(separator)

        self.btn_quick_dashboard = self._create_sidebar_btn()
        self.btn_quick_scanner = self._create_sidebar_btn()
        self.btn_quick_rename = self._create_sidebar_btn()
        self.btn_quick_about = self._create_sidebar_btn()

        sidebar_layout.addWidget(self.btn_quick_dashboard)
        sidebar_layout.addWidget(self.btn_quick_scanner)
        sidebar_layout.addWidget(self.btn_quick_rename)
        sidebar_layout.addWidget(self.btn_quick_about)

        sidebar_layout.addStretch()

        self.btn_lang = QPushButton("🌐 English / فارسی")
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setStyleSheet("""
            QPushButton { background-color: #8c7ae6; color: white; border-radius: 6px; padding: 10px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #9c88ff; }
        """)
        sidebar_layout.addWidget(self.btn_lang)

        self.btn_theme = QPushButton()
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        sidebar_layout.addWidget(self.btn_theme)

        main_layout.addWidget(sidebar)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 15, 15, 15)

        self.stacked_widget = QStackedWidget()
        self.content_layout.addWidget(self.stacked_widget, stretch=1)

        main_layout.addWidget(self.content_widget, stretch=1)
        main_window.setCentralWidget(central_widget)

    def _create_sidebar_btn(self):
        """متد کمکی برای ساخت دکمه‌های سایدبار بدون اتصال سیگنال"""
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setObjectName("sidebarBtn")
        return btn

    def _create_menu_bar(self, main_window):
        """ساخت منوهای نوار بالای نرم‌افزار بدون اتصال سیگنال‌ها"""
        menu_bar = main_window.menuBar()

        self.menu_servers = menu_bar.addMenu("")

        self.menu_servers.setStyleSheet("""
            QMenu {
                min-width: 200px; /* حداقل عرض منو (میتونی کم و زیادش کنی) */
            }
            QMenu::item {
                padding: 8px 40px 8px 20px; /* فاصله دادن به متن برای جلوگیری از تداخل */
            }
        """)

        self.action_import_clipboard = QAction("", main_window)
        self.action_import_clipboard.setShortcut("Ctrl+V")
        self.menu_servers.addAction(self.action_import_clipboard)

        self.action_import_file = QAction("", main_window)
        self.menu_servers.addAction(self.action_import_file)

        self.menu_servers.addSeparator()
        self.action_add_manual = QAction("", main_window)
        self.menu_servers.addAction(self.action_add_manual)

        self.menu_servers.addSeparator()
        self.action_export = QAction("", main_window)
        self.menu_servers.addAction(self.action_export)

