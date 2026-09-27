import os
import json
import base64
import pytest
import subprocess
from PySide6.QtCore import QCoreApplication, QProcess
from domain.models import ProxyConfig
from domain.models.raw_config import RawXrayConfig
from services.core_manager import CoreManager
from services.config_generator import ClientConfigGenerator
from scanner.xray_config_generator import XrayConfigGenerator
from parser.factory import ParserFactory
from config import AppConfig


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


from unittest.mock import patch


@patch("utils.win_job_object.assign_pid_to_job", return_value=True)
def test_bug1_xray_startup_not_killed_prematurely(mock_job, qapp):
    """Verify that CoreManager doesn't kill Xray right after successful start."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    free_port = s.getsockname()[1]
    s.close()

    cm = CoreManager()
    cm.bin_path = AppConfig.XRAY_EXECUTABLE
    if not os.path.exists(cm.bin_path):
        pytest.skip("Xray executable not found")

    logs = []
    cm.log_received.connect(logs.append)

    raw_proxy = RawXrayConfig(
        id=999,
        name="TestRawStartup",
        raw_payload=f'{{"log":{{"loglevel":"none"}},"inbounds":[{{"port":{free_port},"listen":"127.0.0.1","protocol":"mixed"}}],"outbounds":[{{"protocol":"freedom"}}]}}'
    )

    try:
        cm.start_connection(raw_proxy, enable_sys_proxy=False, enable_tun=False)
        assert cm.process.state() == QProcess.ProcessState.Running, f"Logs: {logs}"
        assert cm.is_connected is True, f"Logs: {logs}"
    finally:
        cm.stop_connection(clear_sys_proxy=False)
        assert cm.process.state() == QProcess.ProcessState.NotRunning
        assert cm.is_connected is False


def test_bug2_websocket_config_generation():
    """Verify that websocket transport generates network='ws' and includes wsSettings with path and host."""
    factory = ParserFactory()
    url = "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@1.2.3.4:443?type=ws&security=tls&sni=example.com&path=/custom_ws_path&host=cdn.example.com#TestWS"
    proxy = factory.parse_url(url)

    for gen in (ClientConfigGenerator, XrayConfigGenerator):
        cfg = gen.generate(proxy, 10808)
        stream = cfg["outbounds"][0]["streamSettings"]
        assert stream["network"] == "ws"
        assert "wsSettings" in stream
        assert stream["wsSettings"]["path"] == "/custom_ws_path"
        assert stream["wsSettings"]["headers"]["Host"] == "cdn.example.com"


def test_bug3a_shadowsocks_legacy_trailing_slash():
    """Verify that legacy Base64 Shadowsocks URLs with trailing slash parse without error."""
    factory = ParserFactory()
    plain = "chacha20-ietf-poly1305:iOOVQZSffoCQkvm2SfE2h3@92.118.112.125:443"
    b64 = base64.b64encode(plain.encode()).decode()

    for url in [f"ss://{b64}/#Slash", f"ss://{b64}/?outline=1#QuerySlash"]:
        proxy = factory.parse_url(url)
        assert proxy.protocol == "shadowsocks"
        assert proxy.server == "92.118.112.125"
        assert proxy.port == 443
        assert proxy.method == "chacha20-ietf-poly1305"
        assert proxy.password == "iOOVQZSffoCQkvm2SfE2h3"


def test_bug3b_shadowsocks_config_generation():
    """Verify that shadowsocks protocol generates correct settings instead of None."""
    factory = ParserFactory()
    url = "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTppT09WUVpTZmZvQ1Frdm0yU2ZFMmgz@92.118.112.125:443/?outline=1#TestSS"
    proxy = factory.parse_url(url)
    assert proxy.protocol == "shadowsocks"

    for gen in (ClientConfigGenerator, XrayConfigGenerator):
        cfg = gen.generate(proxy, 10808)
        outbound = cfg["outbounds"][0]
        assert outbound["protocol"] == "shadowsocks"
        assert outbound["settings"] is not None
        assert "servers" in outbound["settings"]
        srv = outbound["settings"]["servers"][0]
        assert srv["address"] == "92.118.112.125"
        assert srv["port"] == 443
        assert srv["method"] == "chacha20-ietf-poly1305"
        assert srv["password"] == "iOOVQZSffoCQkvm2SfE2h3"
