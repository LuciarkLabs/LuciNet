import os
import json
import pytest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import QCoreApplication

from domain.models import ProxyConfig
from parser.factory import ParserFactory
from services.config_generator import ClientConfigGenerator
from repository.sqlite_repo import SQLiteProxyRepository
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from config import AppConfig


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_shadowsocks_table_display_and_filter(qapp):
    """Verify that Shadowsocks proxies display as 'SS' and match both 'ss' and 'shadowsocks' filters."""
    url = "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTppT09WUVpTZmZvQ1Frdm0yU2ZFMmgz@92.118.112.125:443/?outline=1#США 2 🇺🇸"
    proxy = ParserFactory().parse_url(url)
    assert proxy.protocol == "shadowsocks"

    table_model = ProxyTableModel([proxy])
    idx = table_model.index(0, 2)
    assert table_model.data(idx) == "SS"

    sort_model = ProxySortModel()
    sort_model.setSourceModel(table_model)

    sort_model.set_protocol_filter("ss")
    assert sort_model.rowCount() == 1

    sort_model.set_protocol_filter("shadowsocks")
    assert sort_model.rowCount() == 1

    sort_model.set_protocol_filter("SS")
    assert sort_model.rowCount() == 1

    sort_model.set_protocol_filter("vless")
    assert sort_model.rowCount() == 0


@pytest.mark.asyncio
async def test_xhttp_persistence_recovery(tmp_path):
    """Verify that mode and extra are restored from raw_url when loading xhttp proxy from SQLite."""
    db_file = tmp_path / "test_repo.db"
    repo = SQLiteProxyRepository(str(db_file))
    await repo.initialize()

    url = "vless://f96d7828-5e49-4dd6-ba32-fd143103cc7a@probe.medic-ml.ru:443?mode=packet-up&path=%2Fapi%2Ftest&security=reality&encryption=none&pbk=660bDah5b-PtCfAbQ3g2tJySO41zsfaXCPb7L3nQCQc&fp=qq&type=xhttp&sni=probe.medic-ml.ru&sid=e1ac2faf5e5f309e&extra=%7B%22mode%22%3A%22packet-up%22%7D#France"
    proxy = ParserFactory().parse_url(url)

    await repo.save(proxy)
    loaded_proxies = await repo.get_all()
    assert len(loaded_proxies) == 1
    loaded = loaded_proxies[0]

    assert loaded.network == "xhttp"
    assert loaded.mode == "packet-up"
    assert loaded.extra == '{"mode":"packet-up"}'


def test_xhttp_config_generation():
    """Verify that XHTTP config includes inbound-local tag, routeOnly true, and proper TUN routing."""
    url = "vless://f96d7828-5e49-4dd6-ba32-fd143103cc7a@probe.medic-ml.ru:443?mode=auto&path=%2Fapi%2Fv2%2Ftelemetry&security=reality&encryption=none&pbk=660bDah5b-PtCfAbQ3g2tJySO41zsfaXCPb7L3nQCQc&fp=qq&type=xhttp&sni=probe.medic-ml.ru&sid=e1ac2faf5e5f309e#France"
    proxy = ParserFactory().parse_url(url)

    cfg_sys = ClientConfigGenerator.generate(proxy, 10811, enable_tun=False)
    inbound_sys = cfg_sys["inbounds"][0]
    assert inbound_sys["tag"] == "inbound-local"
    assert inbound_sys["sniffing"]["routeOnly"] is True

    outbound = cfg_sys["outbounds"][0]
    assert outbound["protocol"] == "vless"
    assert outbound["streamSettings"]["network"] == "xhttp"
    assert outbound["streamSettings"]["xhttpSettings"]["mode"] == "auto"
    assert outbound["streamSettings"]["xhttpSettings"]["path"] == "/api/v2/telemetry"

    cfg_tun = ClientConfigGenerator.generate(proxy, 10811, enable_tun=True)
    assert len(cfg_tun["inbounds"]) == 2
    assert cfg_tun["inbounds"][0]["tag"] == "inbound-local"
    assert cfg_tun["inbounds"][1]["tag"] == "tun-in"
    assert cfg_tun["inbounds"][1]["sniffing"]["routeOnly"] is True

    dns = cfg_tun["dns"]
    assert "https://dns.google/dns-query" in dns["servers"]

    rules = cfg_tun["routing"]["rules"]
    proxy_rule = [r for r in rules if r.get("outboundTag") == "proxy" and "tun-in" in r.get("inboundTag", [])]
    assert len(proxy_rule) == 1
    assert "inbound-local" in proxy_rule[0]["inboundTag"]

    dns_ip_rule = [r for r in rules if r.get("outboundTag") == "proxy" and r.get("port") == 53 and "8.8.8.8" in r.get("ip", [])]
    assert len(dns_ip_rule) == 1


def test_core_manager_tun_non_admin_fallback(qapp):
    """Verify that CoreManager falls back to system proxy when TUN is requested without admin elevation."""
    from services.core_manager import CoreManager
    from PySide6.QtCore import QProcess

    cm = CoreManager()
    cm.bin_path = AppConfig.XRAY_EXECUTABLE
    logs = []
    cm.log_received.connect(logs.append)

    url = "vless://f96d7828-5e49-4dd6-ba32-fd143103cc7a@probe.medic-ml.ru:443?mode=auto&path=%2Fapi%2Fv2%2Ftelemetry&security=reality&encryption=none&pbk=660bDah5b-PtCfAbQ3g2tJySO41zsfaXCPb7L3nQCQc&fp=qq&type=xhttp&sni=probe.medic-ml.ru&sid=e1ac2faf5e5f309e#France"
    proxy = ParserFactory().parse_url(url)

    with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=0), \
         patch.object(cm.process, "start") as mock_start, \
         patch.object(cm.process, "state", return_value=QProcess.ProcessState.Running), \
         patch.object(cm.process, "waitForStarted", return_value=True), \
         patch.object(cm, "set_system_proxy") as mock_set_proxy:
        cm.start_connection(proxy, enable_tun=True)

        assert any("[هشدار TUN]" in log for log in logs)
        mock_set_proxy.assert_called_with(True, cm.local_port)
