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
from utils.logger import get_logger

logger = get_logger("XrayRunner")

class XrayRunnerPool:
    def __init__(
        self,
        port_manager: PortManager,
        checker: XrayChecker,
        max_concurrent: int = AppConfig.MAX_CONCURRENT_SCANS,
    ):
        self.port_manager = port_manager
        self.checker = checker
        self.executable = AppConfig.XRAY_EXECUTABLE

        self.semaphore = None
        self.spawn_lock = None

    def set_concurrent_limit(self, limit: int):

        self.semaphore = asyncio.Semaphore(limit)
        self.spawn_lock = asyncio.Lock()

        self.port_manager.reset()

    async def _wait_for_port(
        self, port: int, process: asyncio.subprocess.Process, timeout: float = 5.0
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
                await asyncio.sleep(0.5)
                return True
            except (ConnectionRefusedError, asyncio.TimeoutError, OSError):
                await asyncio.sleep(0.1)
        return False

    async def scan_proxy(self, proxy_config) -> ScanResult:
        async with self.semaphore:
            port = await self.port_manager.get_free_port()
            process = None

            try:
                xray_json = XrayConfigGenerator.generate(proxy_config, port)

                with tempfile.TemporaryDirectory() as temp_dir:
                    config_path = Path(temp_dir) / "config.json"
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(xray_json, f)

                    async with self.spawn_lock:

                        cflags = (
                            subprocess.CREATE_NO_WINDOW
                            if sys.platform == "win32"
                            else 0
                        )

                        process = await asyncio.create_subprocess_exec(
                            self.executable,
                            "run",
                            "-c",
                            str(config_path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            creationflags=cflags,
                        )
                        await asyncio.sleep(0.1)

                    is_ready = await self._wait_for_port(port, process)

                    if process.returncode is not None and process.returncode != 0:
                        stdout_data = await process.stdout.read()
                        stderr_data = await process.stderr.read()
                        full_err = (
                            stdout_data.decode("utf-8")
                            + "\n"
                            + stderr_data.decode("utf-8")
                        ).strip()
                        logger.error(
                            f"Xray Crash for '{proxy_config.remark}': {full_err}"
                        )
                        return ScanResult(
                            status="Error",
                            error_message=f"Xray Crash: {full_err[:150]}",
                        )

                    if not is_ready:
                        return ScanResult(
                            status="Error",
                            error_message="Local port failed to bind (Timeout)",
                        )

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

    async def check_download_speed(self, proxy_config) -> float:
        async with self.semaphore:
            port = await self.port_manager.get_free_port()
            process = None
            try:
                xray_json = XrayConfigGenerator.generate(proxy_config, port)
                with tempfile.TemporaryDirectory() as temp_dir:
                    config_path = Path(temp_dir) / "config.json"
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(xray_json, f)

                    async with self.spawn_lock:

                        cflags = (
                            subprocess.CREATE_NO_WINDOW
                            if sys.platform == "win32"
                            else 0
                        )

                        process = await asyncio.create_subprocess_exec(
                            self.executable,
                            "run",
                            "-c",
                            str(config_path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            creationflags=cflags,
                        )
                        await asyncio.sleep(0.1)

                    is_ready = await self._wait_for_port(port, process)
                    if not is_ready:
                        return 0.0

                    return await self.checker.check_speed(port)
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
