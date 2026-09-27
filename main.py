import sys
import os
import asyncio
import time
import ctypes
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt

from repository.sqlite_repo import SQLiteProxyRepository
from parser.factory import ParserFactory
from services.geoip_service import GeoIPService, IPInfoProvider
from scanner.port_manager import PortManager
from scanner.checker import XrayChecker
from scanner.xray_runner import XrayRunnerPool
from services.scan_service import ScanService
from gui.main_window import MainWindow


def get_resource_path(relative_path):
    """
    دریافت مسیر مطلق فایل‌های پک‌شده (مثل عکس‌ها و آیکون‌ها).
    در حالت عادی از همون مسیر پروژه و در حالت exe از داخل پوشه _MEIPASS (همون _internal) می‌خونه.
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def setup_dependencies():
    """
    تزریق وابستگی‌ها (Dependency Injection Container).
    تمام اشیاء مورد نیاز در اینجا ساخته شده و به هم متصل می‌شوند.
    """
    repository = SQLiteProxyRepository()

    loop = asyncio.new_event_loop()
    loop.run_until_complete(repository.initialize())
    loop.close()

    parser_factory = ParserFactory()

    geoip_provider = IPInfoProvider()
    geoip_service = GeoIPService(provider=geoip_provider)

    port_manager = PortManager()
    checker = XrayChecker(geoip_service=geoip_service)

    runner_pool = XrayRunnerPool(port_manager=port_manager, checker=checker)
    scan_service = ScanService(runner_pool=runner_pool, repository=repository)

    try:
        from services.core_manager import CoreManager

        CoreManager.recover_system_proxy_on_startup()
    except Exception as e:
        print(f"[Warning] Startup proxy recovery error: {e}")

    return parser_factory, repository, scan_service


def main():
    app = QApplication(sys.argv)

    icon_path = get_resource_path("assets/icon.ico")
    app.setWindowIcon(QIcon(icon_path))

    splash_path = get_resource_path("assets/splash.PNG")
    splash_pix = QPixmap(splash_path)
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    splash.showMessage(
        "Initializing Core Services and Database...\n",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.white,
    )
    app.processEvents()

    time.sleep(0.3)

    print("Initializing Core Services and Database...")
    parser_factory, repository, scan_service = setup_dependencies()

    splash.showMessage(
        "Loading user interface...\n",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.white,
    )
    app.processEvents()

    time.sleep(0.4)

    window = MainWindow(
        parser_factory=parser_factory, repository=repository, scan_service=scan_service
    )
    window.setWindowIcon(QIcon(icon_path))
    window.show()

    splash.finish(window)

    print("Application started successfully.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
