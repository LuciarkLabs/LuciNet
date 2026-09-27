import asyncio
import json
import os
import ssl
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from config import AppConfig
from domain.models.raw_config import RawXrayConfig
from domain.scan_result import ScanResult
from scanner.checker import XrayChecker
from utils.logger import get_logger

logger = get_logger("RawJsonRunner")

_port_locks: Dict[int, asyncio.Lock] = {}
_port_locks_guard = asyncio.Lock()


async def _get_port_lock(port: int) -> asyncio.Lock:
    async with _port_locks_guard:
        if port not in _port_locks:
            _port_locks[port] = asyncio.Lock()
        return _port_locks[port]


class RawJsonRunner:
    def __init__(self, checker: XrayChecker):
        self.checker = checker
        self.executable = AppConfig.XRAY_EXECUTABLE
        self.probe_mode = "http"

    def set_probe_mode(self, mode: str):
        self.probe_mode = "https" if str(mode).lower() == "https" else "http"

    @staticmethod
    def inspect_client_inbound(payload: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
        """
        Inspects payload (READ-ONLY) to locate a usable local client inbound.
        Returns (inbound_port, inbound_protocol, error_message).
        If invalid JSON or no client inbound, returns (None, None, error_message).
        """
        try:
            cfg = json.loads(payload)
        except Exception as e:
            return None, None, f"Invalid JSON syntax: {e}"

        if not isinstance(cfg, dict):
            return None, None, "JSON root is not an object"

        if not cfg.get("outbounds"):
            return None, None, "JSON config has no outbounds defined"

        inbounds = cfg.get("inbounds")
        if not inbounds or not isinstance(inbounds, list):
            return None, None, "Full JSON has no inbounds defined"

        candidates = []
        for ib in inbounds:
            if not isinstance(ib, dict):
                continue
            prot = str(ib.get("protocol", "")).strip().lower()
            port = ib.get("port")
            try:
                port_int = int(port) if port is not None else None
            except (ValueError, TypeError):
                port_int = None

            if port_int and 1 <= port_int <= 65535:
                if prot in ("mixed", "http", "socks"):
                    candidates.append((port_int, prot))

        if not candidates:
            return None, None, "Full JSON has no usable local client inbound for scanner connectivity probe."

        for port_int, prot in candidates:
            if prot in ("mixed", "http"):
                return port_int, prot, None

        return candidates[0][0], candidates[0][1], None

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

    async def _probe_socks5(
        self,
        local_port: int,
        target_host: str,
        target_port: int,
        path: str,
        timeout: float = 6.0,
        use_tls: bool = False,
    ) -> Tuple[int, str, float]:
        """
        Pure asyncio SOCKS5 client probe: performs SOCKS5 handshake, CONNECT, optional TLS upgrade, and HTTP GET.
        Returns (http_status_code, body_snippet, latency_ms).
        """
        start = time.time()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", local_port),
            timeout=min(timeout, 3.0),
        )
        try:
            writer.write(b"\x05\x01\x00")
            await writer.drain()
            resp = await asyncio.wait_for(reader.readexactly(2), timeout=min(timeout, 3.0))
            if resp != b"\x05\x00":
                raise Exception(f"SOCKS5 auth negotiation failed: {resp.hex()}")

            domain_bytes = target_host.encode("ascii")
            req = (
                b"\x05\x01\x00\x03"
                + bytes([len(domain_bytes)])
                + domain_bytes
                + target_port.to_bytes(2, "big")
            )
            writer.write(req)
            await writer.drain()

            rep_hdr = await asyncio.wait_for(reader.readexactly(4), timeout=min(timeout, 4.0))
            if rep_hdr[1] != 0:
                raise Exception(f"SOCKS5 connect error code: {rep_hdr[1]}")

            atyp = rep_hdr[3]
            if atyp == 1:
                await reader.readexactly(4 + 2)
            elif atyp == 3:
                dlen = (await reader.readexactly(1))[0]
                await reader.readexactly(dlen + 2)
            elif atyp == 4:
                await reader.readexactly(16 + 2)

            if use_tls:
                loop = asyncio.get_running_loop()
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
                protocol = writer.transport.get_protocol()
                new_transport = await asyncio.wait_for(
                    loop.start_tls(writer.transport, protocol, ssl_ctx, server_hostname=target_host),
                    timeout=min(timeout, 4.0),
                )
                writer._transport = new_transport

            http_req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {target_host}\r\n"
                f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
                f"Accept: */*\r\n"
                f"Connection: close\r\n\r\n"
            ).encode("latin1")
            writer.write(http_req)
            await writer.drain()

            status_line = await asyncio.wait_for(reader.readline(), timeout=min(timeout, 4.0))
            latency = round((time.time() - start) * 1000, 2)
            status_str = status_line.decode("latin1", errors="replace").strip()
            parts = status_str.split(" ", 2)
            code = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 0

            body = b""
            try:
                body = await asyncio.wait_for(reader.read(4096), timeout=1.5)
            except Exception:
                pass

            return code, body.decode("latin1", errors="replace"), latency
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def scan_raw_config(self, raw_config: RawXrayConfig) -> ScanResult:
        inbound_port, inbound_proto, err = self.inspect_client_inbound(raw_config.raw_payload)
        if err:
            if "no usable local client inbound" in err or "no inbounds defined" in err:
                return ScanResult(status="Unsupported", error_message=err)
            return ScanResult(status="Invalid", error_message=err)

        port_lock = await _get_port_lock(inbound_port)
        async with port_lock:
            process = None
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    config_path = Path(temp_dir) / "config.json"
                    with open(config_path, "w", encoding="utf-8") as f:
                        f.write(raw_config.raw_payload)

                    cflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

                    test_proc = await asyncio.create_subprocess_exec(
                        self.executable,
                        "run",
                        "-test",
                        "-c",
                        str(config_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        creationflags=cflags,
                    )
                    stdout, stderr = await test_proc.communicate()
                    if test_proc.returncode != 0:
                        err_msg = (stderr or stdout).decode("utf-8", errors="replace").strip()
                        return ScanResult(status="Invalid", error_message=f"Xray test failed: {err_msg}")

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
                            assign_pid_to_job(process.pid)
                        except Exception as e:
                            logger.error(f"Job Object protection failed: {e}")
                            return ScanResult(status="Error", error_message=f"Job Object protection failed: {e}")

                    is_ready = await self._wait_for_port(inbound_port, process, timeout=6.0)

                    if process.returncode is not None and process.returncode != 0:
                        return ScanResult(
                            status="Error",
                            error_message=f"Xray exited with code {process.returncode}",
                        )

                    if not is_ready:
                        return ScanResult(
                            status="Error",
                            error_message=f"Local port {inbound_port} failed to bind (Timeout)",
                        )

                    await asyncio.sleep(0.05)

                    if inbound_proto in ("http", "mixed"):
                        res = await self.checker.check_connection(inbound_port)
                        if res.status == "Invalid" and res.error_message.startswith("HTTP "):
                            res.status = "Error"
                        return res
                    else:
                        probe_mode = getattr(self, "probe_mode", None) or getattr(self.checker, "probe_mode", "http")
                        target_port = 443 if probe_mode == "https" else 80
                        use_tls = (probe_mode == "https")
                        code, _, latency = await self._probe_socks5(
                            inbound_port,
                            "www.gstatic.com",
                            target_port,
                            "/generate_204",
                            timeout=getattr(self.checker, "timeout_seconds", 6.0),
                            use_tls=use_tls,
                        )
                        if code not in (200, 204, 301, 302):
                            err_msg = "Connection closed (EOF)" if code == 0 else f"HTTP {code}"
                            return ScanResult(status="Error", error_message=err_msg)

                        outbound_ip = ""
                        country = ""
                        city = ""
                        isp = ""
                        try:
                            t_code, trace_text, _ = await self._probe_socks5(
                                inbound_port, "1.1.1.1", 80, "/cdn-cgi/trace", timeout=4.0
                            )
                            if t_code == 200:
                                for line in trace_text.splitlines():
                                    if line.startswith("ip="):
                                        outbound_ip = line.split("=")[1].strip()
                                    elif line.startswith("loc="):
                                        country = line.split("=")[1].strip()
                        except Exception:
                            pass

                        if outbound_ip and hasattr(self.checker, "geoip_service") and self.checker.geoip_service:
                            try:
                                geo_data = await self.checker.geoip_service.get_ip_info(outbound_ip)
                                if geo_data:
                                    if not country:
                                        country = geo_data[0]
                                    city = geo_data[1]
                                    isp = geo_data[2]
                            except Exception:
                                pass

                        return ScanResult(
                            status="Valid",
                            latency_ms=latency,
                            country=country,
                            city=city,
                            isp=isp,
                            outbound_ip=outbound_ip,
                        )

            except (asyncio.TimeoutError, TimeoutError):
                return ScanResult(status="Timeout", error_message="Timeout")
            except Exception as e:
                logger.error(f"Raw JSON scan execution error: {e}")
                return ScanResult(status="Error", error_message=str(e))
            finally:
                if process and process.returncode is None:
                    try:
                        process.kill()
                        await process.wait()
                    except (ProcessLookupError, Exception):
                        pass

    async def check_download_speed(self, raw_config: RawXrayConfig, max_size_kb: int = 500) -> float:
        inbound_port, inbound_proto, err = self.inspect_client_inbound(raw_config.raw_payload)
        if err or not inbound_port:
            return 0.0

        port_lock = await _get_port_lock(inbound_port)
        async with port_lock:
            process = None
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    config_path = Path(temp_dir) / "config.json"
                    with open(config_path, "w", encoding="utf-8") as f:
                        f.write(raw_config.raw_payload)

                    cflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

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
                            assign_pid_to_job(process.pid)
                        except Exception:
                            pass

                    is_ready = await self._wait_for_port(inbound_port, process, timeout=6.0)
                    if not is_ready:
                        return 0.0

                    await asyncio.sleep(0.05)

                    if inbound_proto in ("http", "mixed"):
                        return await self.checker.check_speed(inbound_port, max_size_kb)

                    start_time = time.time()
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection("127.0.0.1", inbound_port), timeout=3.0
                    )
                    try:
                        writer.write(b"\x05\x01\x00")
                        await writer.drain()
                        resp = await reader.readexactly(2)
                        if resp != b"\x05\x00":
                            return 0.0

                        domain = b"proof.ovh.net"
                        req = b"\x05\x01\x00\x03" + bytes([len(domain)]) + domain + (80).to_bytes(2, "big")
                        writer.write(req)
                        await writer.drain()

                        rep = await reader.readexactly(4)
                        if rep[1] != 0:
                            return 0.0
                        atyp = rep[3]
                        if atyp == 1:
                            await reader.readexactly(6)
                        elif atyp == 3:
                            dlen = (await reader.readexactly(1))[0]
                            await reader.readexactly(dlen + 2)
                        elif atyp == 4:
                            await reader.readexactly(18)

                        http_req = (
                            b"GET /files/10Mb.dat HTTP/1.1\r\n"
                            b"Host: proof.ovh.net\r\n"
                            b"User-Agent: Mozilla/5.0\r\n"
                            b"Connection: close\r\n\r\n"
                        )
                        writer.write(http_req)
                        await writer.drain()

                        status_line = await reader.readline()
                        if not status_line.startswith(b"HTTP/1.1 200") and not status_line.startswith(b"HTTP/1.0 200"):
                            return 0.0

                        while True:
                            hdr_line = await reader.readline()
                            if hdr_line in (b"\r\n", b"\n", b""):
                                break

                        bytes_to_read = max_size_kb * 1024
                        total = 0
                        while total < bytes_to_read:
                            chunk = await reader.read(8192)
                            if not chunk:
                                break
                            total += len(chunk)

                        duration = time.time() - start_time
                        if duration > 0 and total > 0:
                            speed_bps = total / duration
                            return round(speed_bps / (1024 * 1024), 2)
                        return 0.0
                    finally:
                        writer.close()
                        try:
                            await writer.wait_closed()
                        except Exception:
                            pass

            except Exception as e:
                logger.debug(f"Raw speed test error: {e}")
                return 0.0
            finally:
                if process and process.returncode is None:
                    try:
                        process.kill()
                        await process.wait()
                    except Exception:
                        pass
