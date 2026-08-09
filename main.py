import sys
import asyncio
import time
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

def setup_dependencies():
\
\
\

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

    return parser_factory, repository, scan_service

def main():

    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon("assets/icon.ico"))

    splash_pix = QPixmap("assets/splash.PNG")
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

    time.sleep(1.25)

    print("Initializing Core Services and Database...")
    parser_factory, repository, scan_service = setup_dependencies()

    splash.showMessage(
        "Loading user interface...\n",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
        Qt.GlobalColor.white,
    )
    app.processEvents()

    time.sleep(0.9)

    window = MainWindow(
        parser_factory=parser_factory, repository=repository, scan_service=scan_service
    )
    window.setWindowIcon(QIcon("assets/icon.ico"))
    window.show()

    splash.finish(window)

    print("Application started successfully.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
