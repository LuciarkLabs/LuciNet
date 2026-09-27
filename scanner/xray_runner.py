import time
import asyncio
import tempfile
import json
import subprocess
import sys
from pathlib import Path
from scanner.port_manager import PortManager
from scanner.xray_config_generator import XrayConfigGenerator, XrayConfigValidatorError
from scanner.checker import XrayChecker
from domain.scan_result import ScanResult
from config import AppConfig
from scanner.raw_json_runner import RawJsonRunner
from domain.models.raw_config import RawXrayConfig
from utils.logger import get_logger

logger = get_logger("XrayRunner")


class XrayRunnerPool:
    def __init__(
        self,
        port_manager: PortManager,
        checker: XrayChecker,
    ):
        self.port_manager = port_manager
        self.checker = checker
        self.raw_runner = RawJsonRunner(checker)
        self.executable = AppConfig.XRAY_EXECUTABLE
        self.semaphore = None
        self.probe_mode = "http"

    def set_concurrent_limit(self, limit: int):
        self.semaphore = asyncio.Semaphore(limit)
        self.port_manager.reset()

    def set_probe_mode(self, mode: str):
        self.probe_mode = "https" if str(mode).lower() == "https" else "http"
        if hasattr(self.checker, "set_probe_mode"):
            self.checker.set_probe_mode(self.probe_mode)
        if hasattr(self.raw_runner, "set_probe_mode"):
            self.raw_runner.set_probe_mode(self.probe_mode)

    async def _wait_for_port(
        self, port: int, process: asyncio.subprocess.Process, timeout: float = 6.0
    ) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            if process.returncode is not None:
                return False

            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", port), timeout=0.5
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
                await asyncio.sleep(0.05)
        return False

    async def scan_proxy(self, proxy_config) -> ScanResult:
        if isinstance(proxy_config, RawXrayConfig) or getattr(proxy_config, "is_raw", False):
            return await self.raw_runner.scan_raw_config(proxy_config)

        async with self.semaphore:
            port = await self.port_manager.get_free_port()
            process = None

            try:
                xray_json = XrayConfigGenerator.generate(proxy_config, port)

                if "log" in xray_json:
                    xray_json["log"]["loglevel"] = "none"

                with tempfile.TemporaryDirectory() as temp_dir:
                    config_path = Path(temp_dir) / "config.json"
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(xray_json, f)

                    cflags = (
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )

                    process = await asyncio.create_subprocess_exec(
                        self.executable,
                        "run",
                        "-c",
                        str(config_path),
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                        creationflags=cflags,
                    )
                    if process and process.pid:
                        try:
                            from utils.win_job_object import assign_pid_to_job
                            success = assign_pid_to_job(process.pid)
                            if not success:
                                raise Exception("Job assignment returned False")
                        except Exception as e:
                            logger.error(f"Job Object protection failed: {e}")
                            return ScanResult(status="Error", error_message=f"Job Object protection failed: {e}")

                    is_ready = await self._wait_for_port(port, process, timeout=6.0)

                    if process.returncode is not None and process.returncode != 0:
                        return ScanResult(
                            status="Error",
                            error_message=f"Xray exited with code {process.returncode}",
                        )

                    if not is_ready:
                        return ScanResult(
                            status="Error",
                            error_message="Local port failed to bind (Timeout)",
                        )

                    await asyncio.sleep(0.05)

                    return await self.checker.check_connection(port)

            except XrayConfigValidatorError as e:
                return ScanResult(
                    status="Invalid", error_message=f"Config Validation: {e}"
                )
            except Exception as e:
                logger.error(f"Execution Error: {e}")
                return ScanResult(status="Error", error_message=str(e))

            finally:
                if process and process.returncode is None:
                    try:
                        process.kill()
                        await process.wait()
                    except ProcessLookupError:
                        pass
                await self.port_manager.release_port(port)

    async def check_download_speed(self, proxy_config, max_size_kb: int = 500) -> float:
        if isinstance(proxy_config, RawXrayConfig) or getattr(proxy_config, "is_raw", False):
            return await self.raw_runner.check_download_speed(proxy_config, max_size_kb)

        async with self.semaphore:
            port = await self.port_manager.get_free_port()
            process = None
            try:
                xray_json = XrayConfigGenerator.generate(proxy_config, port)

                if "log" in xray_json:
                    xray_json["log"]["loglevel"] = "none"

                with tempfile.TemporaryDirectory() as temp_dir:
                    config_path = Path(temp_dir) / "config.json"
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(xray_json, f)

                    cflags = (
                        subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    )

                    process = await asyncio.create_subprocess_exec(
                        self.executable,
                        "run",
                        "-c",
                        str(config_path),
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                        creationflags=cflags,
                    )
                    if process and process.pid:
                        try:
                            from utils.win_job_object import assign_pid_to_job
                            success = assign_pid_to_job(process.pid)
                            if not success:
                                raise Exception("Job assignment returned False")
                        except Exception as e:
                            logger.error(f"Job Object protection failed: {e}")
                            return 0.0

                    is_ready = await self._wait_for_port(port, process, timeout=6.0)
                    if not is_ready:
                        return 0.0

                    await asyncio.sleep(0.05)
                    return await self.checker.check_speed(port, max_size_kb)

            except Exception as e:
                logger.error(f"Speed Test Error: {e}")
                return 0.0
            finally:
                if process and process.returncode is None:
                    try:
                        process.kill()
                        await process.wait()
                    except ProcessLookupError:
                        pass
                await self.port_manager.release_port(port)
