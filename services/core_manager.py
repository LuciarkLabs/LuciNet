from config import AppConfig

import os
import sys
import json
import time
import subprocess
import ctypes
import hashlib
import uuid
from PySide6.QtCore import QObject, Signal, QProcess

from services.config_generator import ClientConfigGenerator
from domain.proxy import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from typing import Union, Optional, Tuple


class CoreManager(QObject):
    log_received = Signal(str)
    status_changed = Signal(bool)

    def __init__(self, bin_path="xray_core/xray.exe"):
        super().__init__()
        self.bin_path = bin_path
        self.local_port = 10811
        self.is_connected = False
        self._starting = False
        self._intentional_stop = False

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.stateChanged.connect(self._handle_state_change)
        self.process.errorOccurred.connect(self._handle_process_error)

    def _remove_tun_devices(self):
        """
        پاکسازی آداپتورهای مجازی قدیمی (مبتنی بر GUID)
        """
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
        proxy: Union[ProxyConfig, RawXrayConfig],
        routing_mode: str = "",
        enable_sys_proxy: bool = True,
        enable_tun: bool = False,
    ):
        self._starting = False
        self.stop_connection(clear_sys_proxy=False)

        try:
            if sys.platform == "win32" and enable_tun:
                try:
                    import ctypes
                    is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
                except Exception:
                    is_admin = False

                if not is_admin:
                    self.log_received.emit(
                        "⚠️ [هشدار TUN] برای استفاده از حالت TUN نیاز به اجرای برنامه با دسترسی Administrator است. اتصال به صورت پروکسی سیستم برقرار شد."
                    )
                    enable_tun = False
                    enable_sys_proxy = True

            if sys.platform == "win32" and enable_tun:
                self._remove_tun_devices()

            base_dir = os.path.abspath(os.path.dirname(self.bin_path))
            config_path = str(AppConfig.DATA_DIR / "client_config.json")

            is_raw = isinstance(proxy, RawXrayConfig)
            has_tun = False
            
            if is_raw:
                try:
                    import json
                    data = json.loads(proxy.raw_payload)
                    for ib in data.get("inbounds", []):
                        if isinstance(ib, dict) and ib.get("protocol") == "tun":
                            has_tun = True
                            break
                except Exception:
                    pass

            if is_raw:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write(proxy.raw_payload)
            else:
                config_dict = ClientConfigGenerator.generate(
                    proxy, self.local_port, enable_tun=enable_tun
                )
                import json
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config_dict, f, indent=2)

            self.process.setWorkingDirectory(base_dir)
            self._starting = True
            self.process.start(os.path.abspath(self.bin_path), ["-c", config_path])
            started = self.process.waitForStarted(2000)

            if not started or self.process.state() == QProcess.ProcessState.NotRunning:
                self.log_received.emit("[Core Error] Process failed to start. Rolling back system proxy...")
                self.stop_connection(clear_sys_proxy=True)
                self.status_changed.emit(False)
                return

            raw_sys_proxy_str = None
            if is_raw:
                try:
                    from scanner.raw_json_runner import RawJsonRunner
                    r_port, r_proto, _ = RawJsonRunner.inspect_client_inbound(proxy.raw_payload)
                    if r_port:
                        if r_proto == "socks":
                            raw_sys_proxy_str = f"socks=127.0.0.1:{r_port}"
                        else:
                            raw_sys_proxy_str = f"127.0.0.1:{r_port}"
                except Exception:
                    pass

            if enable_tun:
                if is_raw and not has_tun:
                    self.log_received.emit("در حالت TUN کانفیگ اختصاصی انتخاب شده است ولی فاقد Inbound از نوع TUN است.")
                    if enable_sys_proxy:
                        if raw_sys_proxy_str:
                            self.set_system_proxy(True, self.local_port, proxy_server_str=raw_sys_proxy_str)
                        else:
                            self.set_system_proxy(True, self.local_port)
                else:
                    self.set_system_proxy(False)
                    self.log_received.emit("✅ حالت TUN فعال شد. پروکسی سیستم به دلیل فعال بودن TUN غیرفعال گردید.")
            elif enable_sys_proxy:
                if raw_sys_proxy_str:
                    self.set_system_proxy(True, self.local_port, proxy_server_str=raw_sys_proxy_str)
                else:
                    self.set_system_proxy(True, self.local_port)

        except Exception as e:
            self.log_received.emit(f"[Core Error] خطا در راه‌اندازی هسته: {e}")
            self._starting = False
            self.stop_connection(clear_sys_proxy=True)
            self.status_changed.emit(False)

    def stop_connection(self, clear_sys_proxy=True):
        self._starting = False
        self._intentional_stop = True
        try:
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.kill()
                self.process.waitForFinished(3000)

            if sys.platform == "win32":
                self._remove_tun_devices()

            if clear_sys_proxy:
                self.set_system_proxy(False)

            self.is_connected = False
        finally:
            self._intentional_stop = False

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

    def _handle_process_error(self, error):
        self.log_received.emit(f"[Core Process Error] {error}")
        if self._starting:
            self._starting = False
            self.log_received.emit("[Core Error] Xray failed to start. Rolling back system proxy...")
            self.stop_connection(clear_sys_proxy=True)
            self.status_changed.emit(False)
        elif self.is_connected and not self._intentional_stop:
            self.log_received.emit("[Core Error] Xray encountered runtime error while running. Rolling back system proxy...")
            self.stop_connection(clear_sys_proxy=True)
            self.status_changed.emit(False)

    def _handle_state_change(self, state):
        if state == QProcess.ProcessState.Running:
            self._starting = False
            try:
                from utils.win_job_object import assign_pid_to_job
                success = assign_pid_to_job(self.process.processId())
                if not success:
                    raise Exception("Job Object assignment returned False")
            except Exception as e:
                self.log_received.emit(f"[JobObject Error] Failed to protect Xray process: {e}")
                self.stop_connection(clear_sys_proxy=True)
                return

            self.is_connected = True
            self.status_changed.emit(True)
            self.log_received.emit("✅ هسته‌ی Xray با موفقیت راه‌اندازی شد.")
        elif state == QProcess.ProcessState.NotRunning:
            was_starting = self._starting
            was_connected = self.is_connected
            was_intentional = self._intentional_stop
            self._starting = False
            self.is_connected = False
            self.status_changed.emit(False)
            self.log_received.emit("❌ اتصال Xray قطع شد.")
            if was_starting:
                self.log_received.emit("[Core Error] Process terminated during startup before running. Rolling back system proxy...")
                self.stop_connection(clear_sys_proxy=True)
            elif was_connected and not was_intentional:
                self.log_received.emit("[Core Error] Xray terminated unexpectedly while running. Rolling back system proxy...")
                self.stop_connection(clear_sys_proxy=True)

    @staticmethod
    def _read_registry_setting(key, name: str) -> dict:
        import winreg
        try:
            val, rtype = winreg.QueryValueEx(key, name)
            return {"present": True, "type": rtype, "value": val}
        except FileNotFoundError:
            return {"present": False, "type": None, "value": None}

    @staticmethod
    def _apply_registry_setting(key, name: str, setting: dict):
        import winreg
        if setting.get("present"):
            winreg.SetValueEx(key, name, 0, setting["type"], setting["value"])
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass

    @staticmethod
    def _compare_settings(s1: dict, s2: dict) -> bool:
        if s1.get("present") != s2.get("present"):
            return False
        if not s1.get("present"):
            return True
        if s1.get("type") != s2.get("type"):
            return False
        v1, v2 = s1.get("value"), s2.get("value")
        if type(v1) is not type(v2):
            return False
        return v1 == v2

    @classmethod
    def _compare_registry_states(cls, state1: dict, state2: dict) -> bool:
        for name in ("ProxyEnable", "ProxyServer", "ProxyOverride"):
            if not cls._compare_settings(state1.get(name, {}), state2.get(name, {})):
                return False
        return True

    @staticmethod
    def _compute_sequential_states(original: dict, managed: dict) -> dict:
        s0 = {k: dict(original[k]) for k in ("ProxyEnable", "ProxyServer", "ProxyOverride")}
        s1 = {
            "ProxyEnable": dict(managed["ProxyEnable"]),
            "ProxyServer": dict(original["ProxyServer"]),
            "ProxyOverride": dict(original["ProxyOverride"]),
        }
        s2 = {
            "ProxyEnable": dict(managed["ProxyEnable"]),
            "ProxyServer": dict(managed["ProxyServer"]),
            "ProxyOverride": dict(original["ProxyOverride"]),
        }
        s3 = {k: dict(managed[k]) for k in ("ProxyEnable", "ProxyServer", "ProxyOverride")}
        return {"S0": s0, "S1": s1, "S2": s2, "S3": s3}

    @staticmethod
    def _write_backup_atomic(backup_path, data: dict):
        import uuid
        tmp_path = str(backup_path) + f".tmp.{uuid.uuid4().hex[:8]}"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(backup_path))
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            raise

    @staticmethod
    def _quarantine_backup(backup_path, reason: str) -> bool:
        import uuid
        from pathlib import Path
        p = Path(backup_path)
        if not p.exists():
            return True
        quarantine_path = p.parent / f"sysproxy_backup.{reason}.{uuid.uuid4().hex[:8]}.json"
        try:
            os.replace(str(p), str(quarantine_path))
            return True
        except Exception:
            try:
                os.rename(str(p), str(quarantine_path))
                return True
            except Exception:
                return False

    @classmethod
    def _invalidate_backup_atomic(cls, backup_path) -> bool:
        """
        Atomically invalidate backup file in-place if delete/quarantine failed.
        Creates temporary file, writes invalidation JSON, flushes, fsyncs, and replaces.
        Cleans up temporary file on failure.
        """
        invalidation_data = {
            "version": 1,
            "owner": "LuciNet",
            "phase": "restored_quarantine_failed",
            "invalidated_at": time.time(),
            "note": "Registry was restored, but backup removal and quarantine both failed."
        }
        try:
            cls._write_backup_atomic(backup_path, invalidation_data)
            return True
        except Exception:
            return False

    @classmethod
    def _validate_and_match_backup(cls, backup_path, current_reg: dict) -> tuple[str, Optional[dict]]:
        from pathlib import Path
        p = Path(backup_path)
        if not p.exists():
            return "not_found", None

        def _do_quarantine(reason: str) -> tuple[str, Optional[dict]]:
            if cls._quarantine_backup(p, reason):
                return "quarantined", None
            return "quarantine_failed", None

        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Backup root is not a dict")
        except Exception:
            return _do_quarantine("corrupt")

        if data.get("owner") != "LuciNet":
            return _do_quarantine("unrecognized")
        v_val = data.get("version")
        if type(v_val) is not int or isinstance(v_val, bool) or v_val != 1:
            return _do_quarantine("unsupported_v")
        phase = data.get("phase")
        if phase not in ("applying", "active"):
            return _do_quarantine("invalid")

        original = data.get("original")
        managed = data.get("managed")
        if not isinstance(original, dict) or not isinstance(managed, dict):
            return _do_quarantine("invalid")

        for name in ("ProxyEnable", "ProxyServer", "ProxyOverride"):
            if name not in original or name not in managed:
                return _do_quarantine("invalid")
            for s in (original[name], managed[name]):
                if not isinstance(s, dict) or "present" not in s:
                    return _do_quarantine("invalid")
                if type(s["present"]) is not bool:
                    return _do_quarantine("invalid")
                if s["present"]:
                    if "type" not in s or "value" not in s:
                        return _do_quarantine("invalid")
                else:
                    if s.get("type") is not None or s.get("value") is not None:
                        return _do_quarantine("invalid")

        for s in (original["ProxyEnable"], managed["ProxyEnable"]):
            if s["present"]:
                t = s.get("type")
                v = s.get("value")
                if type(t) is not int or t != 4 or type(v) is not int or isinstance(v, bool) or not (0 <= v <= 0xFFFFFFFF):
                    return _do_quarantine("invalid")

        for name in ("ProxyServer", "ProxyOverride"):
            for s in (original[name], managed[name]):
                if s["present"]:
                    t = s.get("type")
                    v = s.get("value")
                    if type(t) is not int or t not in (1, 2) or type(v) is not str:
                        return _do_quarantine("invalid")

        states = cls._compute_sequential_states(original, managed)

        if phase == "active":
            if cls._compare_registry_states(current_reg, states["S3"]):
                return "matched", data
            else:
                return _do_quarantine("stale")
        elif phase == "applying":
            if any(cls._compare_registry_states(current_reg, states[s]) for s in ("S0", "S1", "S2", "S3")):
                return "matched", data
            else:
                return _do_quarantine("stale")

        return _do_quarantine("invalid")

    @classmethod
    def recover_system_proxy_on_startup(cls, data_dir=None) -> bool:
        if sys.platform != "win32":
            return False
        import winreg
        import ctypes
        from pathlib import Path

        if data_dir is None:
            data_dir = AppConfig.DATA_DIR
        backup_path = Path(data_dir) / "sysproxy_backup.json"
        if not backup_path.exists():
            return False

        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as key:
                current = {
                    name: cls._read_registry_setting(key, name)
                    for name in ("ProxyEnable", "ProxyServer", "ProxyOverride")
                }
        except Exception:
            return False

        status, data = cls._validate_and_match_backup(backup_path, current)
        if status != "matched" or not data:
            return False

        original = data["original"]
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                for name in ("ProxyEnable", "ProxyServer", "ProxyOverride"):
                    cls._apply_registry_setting(key, name, original[name])

            internet_set_option = ctypes.windll.wininet.InternetSetOptionW
            internet_set_option(0, 39, 0, 0)
            internet_set_option(0, 37, 0, 0)

            cleanup_ok = True
            try:
                os.remove(str(backup_path))
            except Exception:
                if not cls._quarantine_backup(backup_path, "restored"):
                    cleanup_ok = False
                    invalidated = cls._invalidate_backup_atomic(backup_path)
                    import logging
                    if invalidated:
                        logging.getLogger(__name__).warning(
                            "[Proxy Recovery Warning] Registry restored to original state, but backup file cleanup "
                            "(delete and quarantine) failed. The backup has been invalidated atomically in-place."
                        )
                    else:
                        logging.getLogger(__name__).warning(
                            "[Proxy Recovery Warning] Registry restored to original state, but backup file cleanup "
                            "(delete, quarantine, and atomic invalidation) all failed."
                        )

            if not cleanup_ok:
                return False

            return True
        except Exception:
            return False

    def set_system_proxy(self, enable: bool, port: int = 10811, proxy_server_str: Optional[str] = None):
        if sys.platform != "win32":
            return
        import winreg
        import ctypes
        from pathlib import Path

        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        backup_path = AppConfig.DATA_DIR / "sysproxy_backup.json"

        if enable:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as key:
                    current_reg = {
                        name: self._read_registry_setting(key, name)
                        for name in ("ProxyEnable", "ProxyServer", "ProxyOverride")
                    }
            except Exception as e:
                self.log_received.emit(f"[Proxy Error] Failed to read current registry: {e}")
                return

            orig_state = None
            if backup_path.exists():
                status, existing_data = self._validate_and_match_backup(backup_path, current_reg)
                if status == "matched" and existing_data:
                    orig_state = existing_data["original"]
                elif status == "quarantined":
                    orig_state = current_reg
                elif status == "quarantine_failed":
                    self.log_received.emit("[Proxy Error] Existing invalid/stale backup could not be quarantined. Aborting to protect state.")
                    return
                else:
                    orig_state = current_reg
            else:
                orig_state = current_reg

            effective_server = proxy_server_str if proxy_server_str else f"127.0.0.1:{port}"
            managed_state = {
                "ProxyEnable": {"present": True, "type": 4, "value": 1},
                "ProxyServer": {"present": True, "type": 1, "value": effective_server},
                "ProxyOverride": {"present": True, "type": 1, "value": "<local>;localhost;127.*;10.*;172.16.*;192.168.*"},
            }

            backup_data = {
                "version": 1,
                "owner": "LuciNet",
                "phase": "applying",
                "created_at": time.time(),
                "original": orig_state,
                "managed": managed_state,
            }

            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as key:
                    rechecked_reg = {
                        name: self._read_registry_setting(key, name)
                        for name in ("ProxyEnable", "ProxyServer", "ProxyOverride")
                    }
            except Exception as e:
                self.log_received.emit(f"[Proxy Error] Pre-write registry re-read failed: {e}")
                return

            if not self._compare_registry_states(current_reg, rechecked_reg):
                self.log_received.emit("[Proxy Error] Registry changed concurrently between snapshot and write. Aborting safely.")
                return

            try:
                self._write_backup_atomic(backup_path, backup_data)
            except Exception as e:
                self.log_received.emit(f"[Proxy Error] Failed to write backup: {e}")
                return

            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                    self._apply_registry_setting(key, "ProxyEnable", managed_state["ProxyEnable"])
                    self._apply_registry_setting(key, "ProxyServer", managed_state["ProxyServer"])
                    self._apply_registry_setting(key, "ProxyOverride", managed_state["ProxyOverride"])

                internet_set_option = ctypes.windll.wininet.InternetSetOptionW
                internet_set_option(0, 39, 0, 0)
                internet_set_option(0, 37, 0, 0)

                backup_data["phase"] = "active"
                self._write_backup_atomic(backup_path, backup_data)
                self.log_received.emit("✅ پروکسی سیستم با موفقیت فعال شد.")
            except Exception as apply_err:
                self.log_received.emit(f"[Proxy Error] Registry write failed during apply: {apply_err}")
                rollback_ok = False
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                        for name in ("ProxyEnable", "ProxyServer", "ProxyOverride"):
                            self._apply_registry_setting(key, name, orig_state[name])
                    internet_set_option = ctypes.windll.wininet.InternetSetOptionW
                    internet_set_option(0, 39, 0, 0)
                    internet_set_option(0, 37, 0, 0)
                    rollback_ok = True
                except Exception as rb_err:
                    self.log_received.emit(f"[Proxy Rollback Error] Immediate rollback failed: {rb_err}")

                if rollback_ok:
                    try:
                        os.remove(str(backup_path))
                    except Exception:
                        self._quarantine_backup(backup_path, "restored")
                raise apply_err
        else:
            if backup_path.exists():
                recovered = self.recover_system_proxy_on_startup(AppConfig.DATA_DIR)
                if recovered:
                    self.log_received.emit("✅ پروکسی سیستم با موفقیت به وضعیت اولیه بازگردانده شد.")
                else:
                    self.log_received.emit("[Proxy Notice] پروکسی سیستم از طریق بکاپ بازیابی نشد یا بکاپ معتبر نبود.")
            return

    def _restore_system_proxy(self):
        """Internal recovery shim."""
        return self.recover_system_proxy_on_startup(AppConfig.DATA_DIR)