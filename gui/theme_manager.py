from PySide6.QtWidgets import QApplication

class ThemeManager:
    is_dark = True

    DARK_QSS = """
    QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    QMainWindow { background-color: #11111b; }
    QTabWidget::pane { border: 1px solid #313244; background-color: #1e1e2e; border-radius: 5px; }
    QTabBar::tab { background-color: #181825; color: #a6adc8; padding: 10px 20px; margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; font-weight: bold; }
    QTabBar::tab:selected { background-color: #89b4fa; color: #11111b; }
    QTabBar::tab:hover:!selected { background-color: #313244; }
    QTableView { background-color: #1e1e2e !important; alternate-background-color: #181825 !important; color: #cdd6f4 !important; gridline-color: #313244 !important; border: 1px solid #313244; outline: none; }
    QHeaderView::section { background-color: #313244 !important; color: #cdd6f4 !important; padding: 5px; border: 1px solid #313244; font-weight: bold; }

    /* اصلاح بریدگی فونت‌های فارسی در تمام کادرهای برنامه */
    QGroupBox { font-weight: bold; border: 1px solid #313244 !important; border-radius: 5px; margin-top: 30px; color: #89b4fa !important; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 4px 10px; top: 0px; }

    QFrame { background-color: #1e1e2e !important; }
    QLineEdit, QComboBox, QSpinBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; padding: 5px; border-radius: 4px; }
    QPushButton { font-weight: bold; border-radius: 5px; padding: 6px 15px; border: none; }
    QPushButton:hover { opacity: 0.8; }
    QMenu { background-color: #1e1e2e; border: 1px solid #313244; }
    QMenu::item:selected { background-color: #313244; }
    QProgressBar { border: 1px solid #313244; border-radius: 5px; text-align: center; color: white; background-color: #181825; }
    QProgressBar::chunk { background-color: #a6e3a1; border-radius: 5px; }
    """

    LIGHT_QSS = """
    QWidget { background-color: #f5f6fa; color: #2f3640; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    QMainWindow { background-color: #e1e2e6; }
    QTabWidget::pane { border: 1px solid #dcdde1; background-color: white; border-radius: 5px; }
    QTabBar::tab { background-color: #dcdde1; color: #7f8fa6; padding: 10px 20px; margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; font-weight: bold; }
    QTabBar::tab:selected { background-color: #0097e6; color: white; }
    QTabBar::tab:hover:!selected { background-color: #bdc3c7; }
    QTableView { background-color: white !important; alternate-background-color: #f1f2f6 !important; color: #2f3640 !important; gridline-color: #dcdde1 !important; border: 1px solid #dcdde1; outline: none; }
    QHeaderView::section { background-color: #2f3640 !important; color: white !important; padding: 5px; border: 1px solid #dcdde1; font-weight: bold; }

    /* اصلاح بریدگی فونت‌های فارسی در تمام کادرهای برنامه */
    QGroupBox { font-weight: bold; border: 1px solid #dcdde1 !important; border-radius: 5px; margin-top: 30px; color: #2f3640 !important; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 4px 10px; top: 0px; }

    QFrame { background-color: white !important; }
    QLineEdit, QComboBox, QSpinBox { background-color: white; color: #2f3640; border: 1px solid #dcdde1; padding: 5px; border-radius: 4px; }
    QPushButton { font-weight: bold; border-radius: 5px; padding: 6px 15px; border: none; }
    QPushButton:hover { opacity: 0.8; }
    QMenu { background-color: white; border: 1px solid #dcdde1; }
    QMenu::item:selected { background-color: #f1f2f6; }
    QProgressBar { border: 1px solid #dcdde1; border-radius: 5px; text-align: center; color: #2f3640; background-color: white; }
    QProgressBar::chunk { background-color: #44bd32; border-radius: 5px; }
    """

    @classmethod
    def apply_theme(cls):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(cls.DARK_QSS if cls.is_dark else cls.LIGHT_QSS)

    @classmethod
    def toggle_theme(cls):
        cls.is_dark = not cls.is_dark
        cls.apply_theme()
        return cls.is_dark
