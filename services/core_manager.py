import os
import sys
import json
import subprocess
import ctypes
import hashlib
import uuid
from PySide6.QtCore import QObject, Signal, QProcess

from services.config_generator import ClientConfigGenerator
from domain.proxy import ProxyConfig

class CoreManager(QObject):
    log_received = Signal(str)
    status_changed = Signal(bool)

    def __init__(self, bin_path="xray_core/xray.exe"):
        super().__init__()
        self.bin_path = bin_path
        self.local_port = 10811
        self.is_connected = False

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.stateChanged.connect(self._handle_state_change)

    def _remove_tun_devices(self):
\
\

        if sys.platform != "win32":
            return

        tun_names = ["LuciNet", "wintunsingbox_tun", "xray_tun"]
        self.log_received.emit("🧹 در حال پاکسازی آداپتورهای مجازی قدیمی...")

        for name in tun_names:
            try:
                md5_bytes = hashlib.md5(name.encode("utf-8")).digest()
                tun_guid = str(uuid.UUID(bytes_le=md5_bytes))

                subprocess.run(
                    ["pnputil.exe", "/remove-device", f"SWD\\Wintun\\{{{tun_guid}}}"],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                self.log_received.emit(f"[TUN Cleanup Warning] {e}")

    def start_connection(
        self,
        proxy: ProxyConfig,
        routing_mode: str = "",
        enable_sys_proxy: bool = True,
        enable_tun: bool = False,
    ):
        self.stop_connection(clear_sys_proxy=False)

        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "xray.exe", "/T"],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                if enable_tun:
                    self._remove_tun_devices()

            base_dir = os.path.abspath(os.path.dirname(self.bin_path))
            config_path = os.path.join(base_dir, "client_config.json")

            config_dict = ClientConfigGenerator.generate(
                proxy, self.local_port, enable_tun=enable_tun
            )

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2)

            self.process.setWorkingDirectory(base_dir)
            self.process.start(os.path.abspath(self.bin_path), ["-c", config_path])

            if enable_tun:
                self.set_system_proxy(False)
                self.log_received.emit(
                    "⚠️ حالت TUN فعال شد. پروکسی سیستم نادیده گرفته می‌شود."
                )
            elif enable_sys_proxy:
                self.set_system_proxy(True, self.local_port)

        except Exception as e:
            self.log_received.emit(f"[Core Error] خطا در راه‌اندازی هسته: {e}")
            self.status_changed.emit(False)

    def stop_connection(self, clear_sys_proxy=True):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(3000)

        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/IM", "xray.exe", "/T"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._remove_tun_devices()

        if clear_sys_proxy:
            self.set_system_proxy(False)

        self.is_connected = False

    def _handle_stdout(self):
        data = (
            self.process.readAllStandardOutput()
            .data()
            .decode("utf-8", errors="replace")
        )
        for line in data.splitlines():
            if line.strip():
                self.log_received.emit(line.strip())

    def _handle_stderr(self):
        data = (
            self.process.readAllStandardError().data().decode("utf-8", errors="replace")
        )
        for line in data.splitlines():
            if line.strip():
                self.log_received.emit(f"[XRAY ERROR] {line.strip()}")

    def _handle_state_change(self, state):
        if state == QProcess.ProcessState.Running:
            self.is_connected = True
            self.status_changed.emit(True)
            self.log_received.emit("✅ هسته‌ی Xray با موفقیت راه‌اندازی شد.")
        elif state == QProcess.ProcessState.NotRunning:
            self.is_connected = False
            self.status_changed.emit(False)
            self.log_received.emit("❌ اتصال Xray قطع شد.")

    def set_system_proxy(self, enable: bool, port: int = 10811):
        if sys.platform != "win32":
            return

        try:
            cflags = subprocess.CREATE_NO_WINDOW
            if enable:
                subprocess.run(
                    [
                        "reg",
                        "add",
                        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
                        "/v",
                        "ProxyEnable",
                        "/t",
                        "REG_DWORD",
                        "/d",
                        "1",
                        "/f",
                    ],
                    creationflags=cflags,
                )
                subprocess.run(
                    [
                        "reg",
                        "add",
                        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
                        "/v",
                        "ProxyServer",
                        "/t",
                        "REG_SZ",
                        "/d",
                        f"127.0.0.1:{port}",
                        "/f",
                    ],
                    creationflags=cflags,
                )
                subprocess.run(
                    [
                        "reg",
                        "add",
                        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
                        "/v",
                        "ProxyOverride",
                        "/t",
                        "REG_SZ",
                        "/d",
                        "<local>;localhost;127.*;10.*;172.16.*;192.168.*",
                        "/f",
                    ],
                    creationflags=cflags,
                )
            else:
                subprocess.run(
                    [
                        "reg",
                        "add",
                        "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
                        "/v",
                        "ProxyEnable",
                        "/t",
                        "REG_DWORD",
                        "/d",
                        "0",
                        "/f",
                    ],
                    creationflags=cflags,
                )

            internet_option_settings_changed = 39
            internet_option_refresh = 37
            internet_set_option = ctypes.windll.wininet.InternetSetOptionW
            internet_set_option(0, internet_option_settings_changed, 0, 0)
            internet_set_option(0, internet_option_refresh, 0, 0)

        except Exception as e:
            self.log_received.emit(f"[System Error] خطا در تنظیم پراکسی ویندوز: {e}")
