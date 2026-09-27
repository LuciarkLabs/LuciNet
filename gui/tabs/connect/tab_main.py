
import sys
import ctypes
from PySide6.QtWidgets import QWidget, QMessageBox, QCheckBox, QApplication
from PySide6.QtCore import QSettings
from gui.language_manager import LanguageManager
from gui.event_bus import event_bus
from services.core_manager import CoreManager
from gui.workers import AsyncTaskWorker
from domain.models.raw_config import RawXrayConfig
from domain.models.proxy import ProxyConfig
from .ui_layout import ConnectUiLayout


class ConnectTab(QWidget):
    def __init__(self, repository, scan_service):
        super().__init__()
        self.repository = repository
        self.scan_service = scan_service
        self.selected_proxy = None
        self.core_manager = CoreManager()

        self.settings = QSettings("LuciNet", "Client")

        self.ui = ConnectUiLayout()
        self.ui.setup_ui(self)
        self._connect_signals()
        self.retranslate_ui()

        self.load_settings()

    def load_settings(self):
        """بازیابی آخرین کانفیگ استفاده شده و وضعیت TUN"""
        tun_state = self.settings.value("tun_enabled", False, type=bool)
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False

        if tun_state and not is_admin:
            tun_state = False
            self.settings.setValue("tun_enabled", False)
        self.ui.chk_tun.setChecked(tun_state)

        last_type = self.settings.value("last_selected_type")
        last_id = self.settings.value("last_selected_id")

        if not last_type and self.settings.value("last_proxy_id"):
            last_type = "proxy"
            last_id = self.settings.value("last_proxy_id")

        if last_type not in ("proxy", "raw"):
            last_type = None

        if last_type and last_id:
            try:
                last_id = int(last_id)
                if last_type == "raw" and hasattr(self.repository, "get_all_raw_configs"):
                    self.worker = AsyncTaskWorker(self.repository.get_all_raw_configs())
                    self.worker.finished_signal.connect(
                        lambda configs: self._restore_last_item(configs, last_id)
                    )
                    self.worker.start()
                else:
                    self.worker = AsyncTaskWorker(self.repository.get_all())
                    self.worker.finished_signal.connect(
                        lambda proxies: self._restore_last_item(proxies, last_id)
                    )
                    self.worker.start()
            except Exception:
                pass

    def _restore_last_item(self, items, last_id):
        for item in items:
            if item.id == last_id:
                self.on_proxy_selected(item)
                break

    def _connect_signals(self):
        self.ui.btn_power.clicked.connect(self.toggle_connection)
        event_bus.proxy_selected.connect(self.on_proxy_selected)

        if hasattr(event_bus, "request_quick_connect"):
            event_bus.request_quick_connect.connect(self.handle_quick_connect)

        self.core_manager.status_changed.connect(self.update_ui_state)
        self.core_manager.log_received.connect(
            lambda msg: event_bus.log_message.emit(msg)
        )

        self.ui.chk_tun.clicked.connect(self.on_tun_clicked)

    def on_proxy_selected(self, proxy):
        self.selected_proxy = proxy
        p_type = "unknown"
        name = "Unknown Config"

        if isinstance(proxy, RawXrayConfig):
            name = proxy.name if proxy.name else "Raw JSON Config"
            p_type = "raw"
        elif isinstance(proxy, ProxyConfig):
            name = proxy.remark if proxy.remark else f"{proxy.server}:{proxy.port}"
            p_type = "proxy"
            
        self.ui.lbl_selected_node.setText(name)

        if proxy and proxy.id and p_type != "unknown":
            self.settings.setValue("last_selected_type", p_type)
            self.settings.setValue("last_selected_id", str(proxy.id))

    def handle_quick_connect(self, proxy):
        if self.core_manager.is_connected:
            self.core_manager.stop_connection()
            if proxy is None:
                return

        if proxy is not None:
            self.on_proxy_selected(proxy)
            self.toggle_connection()

    def toggle_connection(self):
        if not self.selected_proxy:
            QMessageBox.warning(
                self,
                LanguageManager.tr("conn_msg_no_proxy_title"),
                LanguageManager.tr("conn_msg_no_proxy_body"),
            )
            event_bus.request_view_change.emit("archive")
            return

        if self.core_manager.is_connected:
            self.core_manager.stop_connection()
        else:
            self.ui.lbl_status.setText(LanguageManager.tr("conn_status_connecting"))
            self.ui.lbl_status.setStyleSheet(
                "font-size: 26px; font-weight: bold; color: #fbc531;"
            )

            use_tun = self.ui.chk_tun.isChecked()
            self.settings.setValue("tun_enabled", use_tun)

            self.core_manager.start_connection(
                proxy=self.selected_proxy,
                routing_mode="",
                enable_sys_proxy=True,
                enable_tun=use_tun,
            )

    def update_ui_state(self, is_connected):
        event_bus.connection_status_changed.emit(is_connected)
        if is_connected:
            self.ui.btn_power.setText(LanguageManager.tr("conn_btn_disconnect"))
            self.ui.btn_power.setStyleSheet("""
                QPushButton { background-color: #20bf6b; color: white; border-radius: 75px; font-size: 18px; font-weight: bold; border: 6px solid #26de81; }
                QPushButton:hover { background-color: #26de81; }
            """)
            self.ui.lbl_status.setText(LanguageManager.tr("conn_status_connected"))
            self.ui.lbl_status.setStyleSheet(
                "font-size: 26px; font-weight: bold; color: #20bf6b;"
            )
            self.ui.chk_tun.setEnabled(False)
        else:
            self.ui.btn_power.setText(LanguageManager.tr("conn_btn_connect"))
            self.ui.btn_power.setStyleSheet("""
                QPushButton { background-color: #eb3b5a; color: white; border-radius: 75px; font-size: 20px; font-weight: bold; border: 6px solid #fc5c65; }
                QPushButton:hover { background-color: #fc5c65; }
            """)
            self.ui.lbl_status.setText(LanguageManager.tr("conn_status_disconnected"))
            self.ui.lbl_status.setStyleSheet(
                "font-size: 26px; font-weight: bold; color: #eb3b5a;"
            )
            self.ui.chk_tun.setEnabled(True)

    def retranslate_ui(self):
        self.ui.lbl_node_title.setText(LanguageManager.tr("conn_lbl_selected_node"))
        if self.selected_proxy:
            proxy = self.selected_proxy
            name = "Unknown Config"
            if isinstance(proxy, RawXrayConfig):
                name = proxy.name if proxy.name else "Raw JSON Config"
            elif isinstance(proxy, ProxyConfig):
                name = proxy.remark if proxy.remark else f"{proxy.server}:{proxy.port}"
            self.ui.lbl_selected_node.setText(name)
        else:
            self.ui.lbl_selected_node.setText(LanguageManager.tr("conn_no_node"))
        self.update_ui_state(self.core_manager.is_connected)

        self.ui.chk_tun.update()

    def on_tun_clicked(self, checked):
        if not checked:
            self.settings.setValue("tun_enabled", False)
            return

        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False

        if is_admin:
            self.settings.setValue("tun_enabled", True)
            return

        skip_warning = self.settings.value("skip_admin_warning", False, type=bool)

        if not skip_warning:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(LanguageManager.tr("conn_msg_admin_title"))
            msg_box.setText(LanguageManager.tr("conn_msg_admin_body"))
            msg_box.setIcon(QMessageBox.Icon.Warning)

            cb = QCheckBox(LanguageManager.tr("conn_chk_dont_show"))
            msg_box.setCheckBox(cb)

            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            ret = msg_box.exec()

            if ret == QMessageBox.StandardButton.Cancel:
                self.ui.chk_tun.setChecked(False)
                return

            if cb.isChecked():
                self.settings.setValue("skip_admin_warning", True)

        self.settings.setValue("tun_enabled", True)

        try:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
        except Exception:
            pass

        QApplication.instance().quit()
