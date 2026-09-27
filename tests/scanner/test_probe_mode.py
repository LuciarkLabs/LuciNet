import asyncio
import json
import ssl
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from domain.models.raw_config import RawXrayConfig
from domain.proxy import ProxyConfig
from domain.scan_result import ScanResult
from gui.tabs.scanner.managers.scan_manager import ScanManager
from gui.tabs.scanner.tab_main import ScannerTab
from gui.tabs.scanner.translations import FA, EN
from gui.tabs.scanner.ui_layout import ScannerUiLayout
from gui.workers import ScanWorker
from scanner.checker import XrayChecker
from scanner.raw_json_runner import RawJsonRunner
from scanner.xray_runner import XrayRunnerPool
from services.scan_service import ScanService
from gui.language_manager import LanguageManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


RAW_PAYLOAD_SAMPLE = """{
  "log": {"loglevel": "error"},
  "inbounds": [
    {
      "port": 10808,
      "protocol": "socks",
      "settings": {"auth": "noauth", "udp": true, "userLevel": 8},
      "tag": "socks"
    }
  ],
  "outbounds": [
    {
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "example.com",
            "port": 443,
            "users": [{"id": "f96d7828-5e49-4dd6-ba32-fd143103cc7a", "encryption": "none"}]
          }
        ]
      },
      "streamSettings": {"network": "tcp", "security": "none"},
      "tag": "proxy"
    }
  ]
}"""


def test_ui_probe_mode_defaults_and_exclusive_selection(qapp):
    widget = QWidget()
    ui = ScannerUiLayout()
    ui.setup_ui(widget)

    assert hasattr(ui, "rb_probe_http"), "rb_probe_http must exist in ui_layout"
    assert hasattr(ui, "rb_probe_https"), "rb_probe_https must exist in ui_layout"
    assert hasattr(ui, "probe_group"), "probe_group must exist in ui_layout"

    assert ui.rb_probe_http.isChecked() is True
    assert ui.rb_probe_https.isChecked() is False

    ui.rb_probe_https.setChecked(True)
    assert ui.rb_probe_http.isChecked() is False
    assert ui.rb_probe_https.isChecked() is True

    ui.rb_probe_http.setChecked(True)
    assert ui.rb_probe_http.isChecked() is True
    assert ui.rb_probe_https.isChecked() is False


def test_ui_probe_mode_labels_exact_text():
    assert FA.get("scn_probe_http") == "HTTP 80"
    assert FA.get("scn_probe_https") == "HTTPS 443"
    assert EN.get("scn_probe_http") == "HTTP 80"
    assert EN.get("scn_probe_https") == "HTTPS 443"


def test_ui_probe_mode_enabled_disabled_with_scanner_state(qapp):
    mock_scan_service = MagicMock(spec=ScanService)
    mock_repo = MagicMock()
    with patch("gui.tabs.scanner.managers.data_manager.DataManager.load_groups"):
        tab = ScannerTab(mock_repo, mock_scan_service)

    assert tab.ui.rb_probe_http.isEnabled() is True
    assert tab.ui.rb_probe_https.isEnabled() is True

    tab.scan_manager.is_running = True
    tab._refresh_ui_state()
    assert tab.ui.rb_probe_http.isEnabled() is False
    assert tab.ui.rb_probe_https.isEnabled() is False

    tab.scan_manager.is_running = False
    tab._refresh_ui_state()
    assert tab.ui.rb_probe_http.isEnabled() is True
    assert tab.ui.rb_probe_https.isEnabled() is True


def test_ui_pass_scan_params_http_and_https(qapp):
    mock_scan_service = MagicMock(spec=ScanService)
    mock_repo = MagicMock()
    with patch("gui.tabs.scanner.managers.data_manager.DataManager.load_groups"):
        tab = ScannerTab(mock_repo, mock_scan_service)

    tab.ui.rb_probe_http.setChecked(True)
    tab._pass_scan_params()
    assert tab.scan_manager.probe_mode == "http"

    tab.ui.rb_probe_https.setChecked(True)
    tab._pass_scan_params()
    assert tab.scan_manager.probe_mode == "https"


def test_scan_manager_default_and_set_params():
    mock_scan_service = MagicMock(spec=ScanService)
    manager = ScanManager(mock_scan_service)

    assert manager.probe_mode == "http"

    manager.set_scan_params(concurrent=20, timeout=10, enable_deep_scan=True, probe_mode="https")
    assert manager.probe_mode == "https"
    assert manager.deep_scan_enabled is True


def test_scan_manager_passes_probe_mode_to_worker():
    mock_scan_service = MagicMock(spec=ScanService)
    manager = ScanManager(mock_scan_service)
    manager.set_scan_params(concurrent=10, timeout=5, enable_deep_scan=False, probe_mode="https")

    proxy = ProxyConfig(protocol="vless", server="1.1.1.1", port=443, user_id="abc")

    with patch.object(ScanWorker, "start") as mock_start:
        manager.start_scan([proxy])
        assert manager.worker is not None
        assert manager.worker.probe_mode == "https"
        mock_start.assert_called_once()


def test_scan_manager_deep_scan_preserves_https_mode():
    mock_scan_service = MagicMock(spec=ScanService)
    manager = ScanManager(mock_scan_service)
    manager.set_scan_params(concurrent=10, timeout=5, enable_deep_scan=True, probe_mode="https")

    p1 = ProxyConfig(protocol="vless", server="1.1.1.1", port=443, user_id="abc")
    p1.status = "Error"
    p2 = ProxyConfig(protocol="vless", server="2.2.2.2", port=443, user_id="def")
    p2.status = "Valid"

    with patch.object(ScanWorker, "start"):
        manager.start_scan([p1, p2])
        assert manager.worker.probe_mode == "https"

        with patch.object(manager, "start_scan", wraps=manager.start_scan) as spy_start:
            manager._on_finished()
            assert spy_start.called
            assert manager.probe_mode == "https"
            assert manager.worker.probe_mode == "https"


def test_scan_manager_deep_scan_preserves_http_mode():
    mock_scan_service = MagicMock(spec=ScanService)
    manager = ScanManager(mock_scan_service)
    manager.set_scan_params(concurrent=10, timeout=5, enable_deep_scan=True, probe_mode="http")

    p1 = ProxyConfig(protocol="vless", server="1.1.1.1", port=443, user_id="abc")
    p1.status = "Timeout"

    with patch.object(ScanWorker, "start"):
        manager.start_scan([p1])
        assert manager.worker.probe_mode == "http"

        with patch.object(manager, "start_scan", wraps=manager.start_scan) as spy_start:
            manager._on_finished()
            assert spy_start.called
            assert manager.probe_mode == "http"
            assert manager.worker.probe_mode == "http"


@pytest.mark.asyncio
async def test_scan_service_propagates_probe_mode():
    mock_runner = MagicMock(spec=XrayRunnerPool)
    mock_runner.checker = MagicMock()
    mock_repo = AsyncMock()

    service = ScanService(mock_runner, mock_repo)
    proxies = [ProxyConfig(protocol="vless", server="1.1.1.1", port=443, user_id="abc")]

    mock_runner.scan_proxy = AsyncMock(return_value=ScanResult(status="Valid", latency_ms=50.0))

    await service.scan_all(
        proxies=proxies,
        on_progress=lambda p, m: None,
        concurrent_scans=1,
        timeout_seconds=5,
        probe_mode="https",
    )

    mock_runner.set_probe_mode.assert_called_once_with("https")


def test_xray_runner_pool_set_probe_mode():
    checker = MagicMock(spec=XrayChecker)
    port_mgr = MagicMock()
    pool = XrayRunnerPool(port_mgr, checker)

    assert pool.probe_mode == "http"
    assert pool.raw_runner.probe_mode == "http"

    pool.set_probe_mode("https")
    assert pool.probe_mode == "https"
    assert pool.raw_runner.probe_mode == "https"
    checker.set_probe_mode.assert_called_with("https")

    pool.set_probe_mode("http")
    assert pool.probe_mode == "http"
    assert pool.raw_runner.probe_mode == "http"
    checker.set_probe_mode.assert_called_with("http")


class MockResponse:
    def __init__(self, status, text_data=""):
        self.status = status
        self.text_data = text_data

    async def text(self):
        return self.text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


@pytest.mark.asyncio
async def test_xray_checker_url_http_mode():
    checker = XrayChecker(None)
    checker.set_probe_mode("http")

    requested_urls = []

    def mock_get(url, *args, **kwargs):
        requested_urls.append(url)
        if "generate_204" in url:
            return MockResponse(204)
        return MockResponse(200)

    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        res = await checker.check_connection(10800)
        assert res.status == "Valid"
        assert "http://www.gstatic.com/generate_204" in requested_urls
        assert "https://www.gstatic.com/generate_204" not in requested_urls


@pytest.mark.asyncio
async def test_xray_checker_url_https_mode():
    checker = XrayChecker(None)
    checker.set_probe_mode("https")

    requested_urls = []

    def mock_get(url, *args, **kwargs):
        requested_urls.append(url)
        if "generate_204" in url:
            return MockResponse(204)
        return MockResponse(200)

    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        res = await checker.check_connection(10800)
        assert res.status == "Valid"
        assert "https://www.gstatic.com/generate_204" in requested_urls
        assert "http://www.gstatic.com/generate_204" not in requested_urls


def _mock_xray_lifecycle():
    mock_test_proc = MagicMock()
    mock_test_proc.returncode = 0
    mock_test_proc.communicate = MagicMock(return_value=asyncio.sleep(0, result=(b"Configuration OK.", b"")))

    mock_run_proc = MagicMock()
    mock_run_proc.pid = 9999
    mock_run_proc.returncode = None
    mock_run_proc.wait = MagicMock(return_value=asyncio.sleep(0, result=0))
    mock_run_proc.kill = MagicMock()

    return mock_test_proc, mock_run_proc


@pytest.mark.asyncio
async def test_raw_json_runner_http_mode_calls_probe_socks5_port_80():
    checker = MagicMock(spec=XrayChecker)
    checker.timeout_seconds = 5.0
    runner = RawJsonRunner(checker)
    runner.set_probe_mode("http")

    raw_cfg = RawXrayConfig(name="NL", raw_payload=RAW_PAYLOAD_SAMPLE)
    mock_test_proc, mock_run_proc = _mock_xray_lifecycle()

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", return_value=(204, "", 120.0)) as mock_probe:

        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Valid"
        first_call = mock_probe.call_args_list[0]
        assert first_call[0][2] == 80
        assert first_call[1].get("use_tls") is False


@pytest.mark.asyncio
async def test_raw_json_runner_https_mode_calls_probe_socks5_port_443_tls():
    checker = MagicMock(spec=XrayChecker)
    checker.timeout_seconds = 5.0
    runner = RawJsonRunner(checker)
    runner.set_probe_mode("https")

    raw_cfg = RawXrayConfig(name="NL", raw_payload=RAW_PAYLOAD_SAMPLE)
    mock_test_proc, mock_run_proc = _mock_xray_lifecycle()

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", return_value=(204, "", 150.0)) as mock_probe:

        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Valid"
        first_call = mock_probe.call_args_list[0]
        assert first_call[0][2] == 443
        assert first_call[1].get("use_tls") is True


@pytest.mark.asyncio
async def test_raw_json_runner_https_tls_ssl_error_yields_error():
    """Real TLS handshake failure (e.g. SSLError) must be classified as Error, NOT Invalid."""
    checker = MagicMock(spec=XrayChecker)
    checker.timeout_seconds = 5.0
    runner = RawJsonRunner(checker)
    runner.set_probe_mode("https")

    raw_cfg = RawXrayConfig(name="NL", raw_payload=RAW_PAYLOAD_SAMPLE)
    mock_test_proc, mock_run_proc = _mock_xray_lifecycle()

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", side_effect=ssl.SSLError("SSL handshake failed: CERTIFICATE_VERIFY_FAILED")):

        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Error"
        assert result.status != "Invalid"
        assert "SSL handshake failed" in result.error_message


@pytest.mark.asyncio
async def test_raw_json_runner_https_tls_timeout_yields_timeout():
    checker = MagicMock(spec=XrayChecker)
    checker.timeout_seconds = 5.0
    runner = RawJsonRunner(checker)
    runner.set_probe_mode("https")

    raw_cfg = RawXrayConfig(name="NL", raw_payload=RAW_PAYLOAD_SAMPLE)
    mock_test_proc, mock_run_proc = _mock_xray_lifecycle()

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", side_effect=asyncio.TimeoutError()):

        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Timeout"


@pytest.mark.asyncio
async def test_raw_json_immutability_both_modes():
    """Payload written to config.json must remain byte-for-byte identical in both HTTP and HTTPS modes."""
    checker = MagicMock(spec=XrayChecker)
    runner = RawJsonRunner(checker)

    raw_cfg = RawXrayConfig(name="NL", raw_payload=RAW_PAYLOAD_SAMPLE)
    mock_test_proc, mock_run_proc = _mock_xray_lifecycle()

    written_contents = []

    def mock_write(self, data):
        written_contents.append(data)

    for mode in ["http", "https"]:
        runner.set_probe_mode(mode)
        written_contents.clear()
        with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
             patch.object(runner, "_wait_for_port", return_value=True), \
             patch.object(runner, "_probe_socks5", return_value=(204, "", 100.0)), \
             patch("pathlib.Path.write_text", side_effect=mock_write):
            await runner.scan_raw_config(raw_cfg)

        assert raw_cfg.raw_payload == RAW_PAYLOAD_SAMPLE


def test_ui_scan_selected_preserves_probe_mode(qapp):
    mock_scan_service = MagicMock(spec=ScanService)
    mock_repo = MagicMock()
    with patch("gui.tabs.scanner.managers.data_manager.DataManager.load_groups"):
        tab = ScannerTab(mock_repo, mock_scan_service)

    p1 = ProxyConfig(protocol="vless", server="1.1.1.1", port=443, user_id="abc")
    tab.model.update_data([p1])

    tab.ui.rb_probe_https.setChecked(True)

    with patch.object(tab, "_get_selected_proxies", return_value=[p1]), \
         patch.object(tab.scan_manager, "start_scan") as mock_start_scan:
        tab._start_selected_scan()
        assert tab.scan_manager.probe_mode == "https"
        mock_start_scan.assert_called_once_with([p1])


@pytest.mark.asyncio
async def test_probe_socks5_direct_tls_upgrade_flow():
    """Unit test _probe_socks5 directly: verify SOCKS5 handshake, CONNECT, loop.start_tls, and HTTP GET."""
    checker = MagicMock(spec=XrayChecker)
    runner = RawJsonRunner(checker)

    mock_reader = AsyncMock()
    mock_reader.readexactly = AsyncMock(side_effect=[
        b"\x05\x00",
        b"\x05\x00\x00\x01",
        b"\x7f\x00\x00\x01\x1f\x90",
    ])
    mock_reader.readline = AsyncMock(return_value=b"HTTP/1.1 204 No Content\r\n")
    mock_reader.read = AsyncMock(return_value=b"")

    mock_writer = MagicMock()
    mock_writer.drain = AsyncMock()
    mock_writer.close = MagicMock()
    mock_writer.wait_closed = AsyncMock()
    mock_writer.transport = MagicMock()

    mock_loop = MagicMock()
    mock_loop.start_tls = AsyncMock(return_value=MagicMock())

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)), \
         patch("asyncio.get_running_loop", return_value=mock_loop):

        code, body, latency = await runner._probe_socks5(
            local_port=10808,
            target_host="www.gstatic.com",
            target_port=443,
            path="/generate_204",
            timeout=5.0,
            use_tls=True,
        )

        assert code == 204
        assert latency >= 0
        mock_loop.start_tls.assert_called_once()
        assert mock_loop.start_tls.call_args[1].get("server_hostname") == "www.gstatic.com"

