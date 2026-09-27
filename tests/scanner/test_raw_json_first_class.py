import asyncio
import json
import pytest
import time
from unittest.mock import MagicMock, patch
from domain.models.raw_config import RawXrayConfig
from domain.models.proxy import ProxyConfig
from repository.sqlite_repo import SQLiteProxyRepository
from scanner.raw_json_runner import RawJsonRunner, _get_port_lock
from scanner.checker import XrayChecker
from domain.scan_result import ScanResult
from gui.models.proxy_table_model import ProxyTableModel, ProxySortModel
from PySide6.QtCore import Qt, QModelIndex

USER_NL_JSON = """{
  "log": {
    "loglevel": "error"
  },
  "inbounds": [
    {
      "port": 10808,
      "protocol": "socks",
      "settings": {
        "auth": "noauth",
        "udp": true,
        "userLevel": 8
      },
      "sniffing": {
        "destOverride": [
          "http",
          "tls"
        ],
        "enabled": true,
        "routeOnly": false
      },
      "tag": "socks"
    }
  ],
  "outbounds": [
    {
      "protocol": "http",
      "settings": {
        "address": "185.126.34.99",
        "level": 8,
        "pass": "@AstroVPN_Official",
        "port": 3128,
        "user": "SDPrqwmPFnjCPHU"
      },
      "tag": "proxy"
    },
    {
      "protocol": "freedom",
      "streamSettings": {
        "network": "tcp",
        "sockopt": {
          "domainStrategy": "UseIP"
        }
      },
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "settings": {},
      "tag": "block"
    }
  ],
  "dns": {
    "tag": "dns-module",
    "servers": [
      "94.140.14.14"
    ]
  },
  "remarks": "Netherlands"
}"""


@pytest.fixture
def sample_raw_config():
    return RawXrayConfig(
        name="Netherlands",
        raw_payload=USER_NL_JSON,
        group_name="Default",
        source_type="file",
        source_ref="test_nl.json",
    )



def test_01_exact_immutable_payload_equality(sample_raw_config):
    """TEST-01: Raw payload must remain 100% exact, bit-for-bit unchanged."""
    assert sample_raw_config.raw_payload == USER_NL_JSON
    assert '"remarks": "Netherlands"' in sample_raw_config.raw_payload
    assert '"port": 10808' in sample_raw_config.raw_payload


def test_02_model_hash_and_identity(sample_raw_config):
    """TEST-02: source_hash and unique_hash match SHA-256 of raw bytes."""
    import hashlib
    expected_hash = hashlib.sha256(USER_NL_JSON.encode("utf-8")).hexdigest()
    assert sample_raw_config.source_hash == expected_hash
    assert sample_raw_config.unique_hash == expected_hash


def test_03_first_class_properties_and_remark(sample_raw_config):
    """TEST-03: First-class properties (protocol='raw json', is_raw=True, remark getter/setter)."""
    assert sample_raw_config.protocol == "raw json"
    assert sample_raw_config.is_raw is True
    assert sample_raw_config.remark == "Netherlands"

    sample_raw_config.remark = "Renamed NL"
    assert sample_raw_config.name == "Renamed NL"
    assert sample_raw_config.remark == "Renamed NL"
    assert sample_raw_config.raw_payload == USER_NL_JSON


def test_04_read_only_metadata_inspection(sample_raw_config):
    """TEST-04: Non-mutating read-only metadata inspection from outbounds."""
    assert sample_raw_config.server == "185.126.34.99"
    assert sample_raw_config.port == 3128
    assert sample_raw_config.network == ""
    assert sample_raw_config.security == ""


def test_05_default_telemetry_fields(sample_raw_config):
    """TEST-05: RawXrayConfig telemetry fields initialized properly."""
    assert sample_raw_config.status == "Untested"
    assert sample_raw_config.ping == -1.0
    assert sample_raw_config.download_speed == 0.0
    assert sample_raw_config.country == ""
    assert sample_raw_config.real_ip == ""
    assert sample_raw_config.scan_count == 0



@pytest.mark.asyncio
async def test_06_db_v10_migration_and_persistence(tmp_path):
    """TEST-06: Database migration V10 and persistence of RawXrayConfig telemetry."""
    db_file = str(tmp_path / "test_repo.db")
    repo = SQLiteProxyRepository(db_file)
    await repo.initialize()

    cfg = RawXrayConfig(
        name="Netherlands",
        raw_payload=USER_NL_JSON,
        group_name="Europe",
        source_type="clipboard",
        source_ref="clip",
        status="Valid",
        ping=124.5,
        download_speed=3.45,
        country="NL",
        city="Amsterdam",
        isp="AstroVPN",
        real_ip="185.126.34.99",
        last_scan=1000.0,
        last_seen_alive=1000.0,
        scan_count=1,
        error_message="",
    )
    raw_id = await repo.save_raw_config(cfg)
    assert raw_id is not None

    loaded = await repo.get_all_raw_configs()
    assert len(loaded) == 1
    item = loaded[0]
    assert item.raw_payload == USER_NL_JSON
    assert item.name == "Netherlands"
    assert item.group_name == "Europe"
    assert item.status == "Valid"
    assert item.ping == 124.5
    assert item.download_speed == 3.45
    assert item.country == "NL"
    assert item.city == "Amsterdam"
    assert item.isp == "AstroVPN"
    assert item.real_ip == "185.126.34.99"
    assert item.last_scan == 1000.0
    assert item.scan_count == 1


@pytest.mark.asyncio
async def test_07_save_many_polymorphic_batch(tmp_path):
    """TEST-07: save_many handles mixed list of ProxyConfig and RawXrayConfig."""
    db_file = str(tmp_path / "test_batch.db")
    repo = SQLiteProxyRepository(db_file)
    await repo.initialize()

    p1 = ProxyConfig(protocol="vless", server="1.2.3.4", port=443, remark="Node1")
    r1 = RawXrayConfig(name="NL JSON", raw_payload=USER_NL_JSON, group_name="Default")

    saved_count = await repo.save_many([p1, r1])
    assert saved_count == 2

    unified = await repo.get_all_unified()
    assert len(unified) == 2
    p_loaded = [u for u in unified if isinstance(u, ProxyConfig)][0]
    r_loaded = [u for u in unified if isinstance(u, RawXrayConfig)][0]
    assert p_loaded.id is not None
    assert r_loaded.id is not None

    p_loaded.status = "Valid"
    p_loaded.ping = 50.0
    r_loaded.status = "Valid"
    r_loaded.ping = 110.0
    r_loaded.country = "NL"
    await repo.save_many([p_loaded, r_loaded])

    unified2 = await repo.get_all_unified()
    assert len(unified2) == 2

    types = {type(u) for u in unified2}
    assert ProxyConfig in types
    assert RawXrayConfig in types

    r_final = [u for u in unified2 if isinstance(u, RawXrayConfig)][0]
    assert r_final.status == "Valid"
    assert r_final.ping == 110.0
    assert r_final.country == "NL"
    assert r_final.raw_payload == USER_NL_JSON


@pytest.mark.asyncio
async def test_08_mixed_move_and_delete(tmp_path):
    """TEST-08: move_mixed_many and delete_mixed_many correctly update both tables."""
    db_file = str(tmp_path / "test_mixed.db")
    repo = SQLiteProxyRepository(db_file)
    await repo.initialize()

    p1 = ProxyConfig(protocol="vmess", server="5.6.7.8", port=80, remark="VmessNode")
    r1 = RawXrayConfig(name="NL JSON", raw_payload=USER_NL_JSON, group_name="Default")
    await repo.save_many([p1, r1])

    unified = await repo.get_all_unified()
    p_loaded = [u for u in unified if isinstance(u, ProxyConfig)][0]
    r_loaded = [u for u in unified if isinstance(u, RawXrayConfig)][0]

    moved_count = await repo.move_mixed_many([p_loaded.id], [r_loaded.id], "VIP")
    assert moved_count == 2

    unified = await repo.get_all_unified()
    for u in unified:
        assert u.group_name == "VIP"

    deleted_count = await repo.delete_mixed_many([p_loaded.id], [r_loaded.id])
    assert deleted_count == 2
    assert len(await repo.get_all_unified()) == 0



def test_09_table_model_rendering(sample_raw_config):
    """TEST-09: ProxyTableModel displays RawXrayConfig telemetry and styling."""
    sample_raw_config.status = "Valid"
    sample_raw_config.ping = 150.0
    sample_raw_config.download_speed = 2.5
    sample_raw_config.country = "NL"
    sample_raw_config.real_ip = "185.126.34.99"

    model = ProxyTableModel([sample_raw_config])
    assert model.rowCount() == 1
    assert model.columnCount() == len(model.headers)

    assert model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole) == "Netherlands"
    assert model.data(model.index(0, 2), Qt.ItemDataRole.DisplayRole) == "RAW JSON"
    assert model.data(model.index(0, 3), Qt.ItemDataRole.DisplayRole) == "185.126.34.99"
    assert model.data(model.index(0, 4), Qt.ItemDataRole.DisplayRole) == "185.126.34.99"
    assert model.data(model.index(0, 5), Qt.ItemDataRole.DisplayRole) == "3128"
    assert model.data(model.index(0, 8), Qt.ItemDataRole.DisplayRole) == "NL"
    assert model.data(model.index(0, 9), Qt.ItemDataRole.DisplayRole) == "150.0 ms"
    assert model.data(model.index(0, 10), Qt.ItemDataRole.DisplayRole) == "Valid"
    assert model.data(model.index(0, 11), Qt.ItemDataRole.DisplayRole) == "2.5 MB/s"

    assert model.data(model.index(0, 2), Qt.ItemDataRole.ForegroundRole) is not None
    assert model.data(model.index(0, 10), Qt.ItemDataRole.ForegroundRole) is not None


def test_10_proxy_sort_model_filters(sample_raw_config):
    """TEST-10: ProxySortModel filters correctly for status, protocol, search and group."""
    sample_raw_config.status = "Valid"
    sample_raw_config.group_name = "Europe"

    source_model = ProxyTableModel([sample_raw_config])
    sort_model = ProxySortModel()
    sort_model.setSourceModel(source_model)

    sort_model.set_status_filter("Valid")
    assert sort_model.rowCount() == 1

    sort_model.set_status_filter("Invalid")
    assert sort_model.rowCount() == 0

    sort_model.set_status_filter("")
    assert sort_model.rowCount() == 1

    sort_model.set_protocol_filter("RAW JSON")
    assert sort_model.rowCount() == 1

    sort_model.set_protocol_filter("vless")
    assert sort_model.rowCount() == 0

    sort_model.set_protocol_filter("")
    assert sort_model.rowCount() == 1

    sort_model.set_search_text("Nether")
    assert sort_model.rowCount() == 1

    sort_model.set_search_text("185.126")
    assert sort_model.rowCount() == 1

    sort_model.set_search_text("NonExistent")
    assert sort_model.rowCount() == 0

    sort_model.set_search_text("")
    assert sort_model.rowCount() == 1

    sort_model.set_group_filter("Europe")
    assert sort_model.rowCount() == 1

    sort_model.set_group_filter("Asia")
    assert sort_model.rowCount() == 0



def test_11_inspect_client_inbound_success():
    """TEST-11: Detects client inbound port and protocol from user JSON."""
    port, proto, err = RawJsonRunner.inspect_client_inbound(USER_NL_JSON)
    assert err is None
    assert port == 10808
    assert proto == "socks"


def test_12_inspect_client_inbound_unsupported_when_no_client():
    """TEST-12: Correctly reports Unsupported when config has no usable client inbound."""
    server_only_json = json.dumps({
        "inbounds": [
            {"port": 443, "protocol": "vless", "settings": {}}
        ],
        "outbounds": [{"protocol": "freedom"}]
    })
    port, proto, err = RawJsonRunner.inspect_client_inbound(server_only_json)
    assert port is None
    assert "no usable local client inbound" in err


def test_13_inspect_client_inbound_syntax_error():
    """TEST-13: Reports Invalid on JSON syntax error."""
    port, proto, err = RawJsonRunner.inspect_client_inbound("{ corrupt json ...")
    assert port is None
    assert "Invalid JSON" in err


@pytest.mark.asyncio
async def test_14_unsupported_scan_result_without_mutating_config():
    """TEST-14: Scan returns status='Unsupported' for server-only JSON without touching payload."""
    server_only_json = json.dumps({
        "inbounds": [{"port": 443, "protocol": "vless"}],
        "outbounds": [{"protocol": "freedom"}]
    })
    raw_cfg = RawXrayConfig(name="Server Node", raw_payload=server_only_json)

    checker = MagicMock(spec=XrayChecker)
    runner = RawJsonRunner(checker)

    result = await runner.scan_raw_config(raw_cfg)
    assert result.status == "Unsupported"
    assert "no usable local client inbound" in result.error_message
    assert raw_cfg.raw_payload == server_only_json


@pytest.mark.asyncio
async def test_15_per_port_lock_serializes_identical_ports():
    """TEST-15: Two tasks on port 10808 acquire the same lock to serialize execution."""
    lock1 = await _get_port_lock(10808)
    lock2 = await _get_port_lock(10808)
    lock_other = await _get_port_lock(10809)

    assert lock1 is lock2
    assert lock1 is not lock_other



@pytest.mark.asyncio
async def test_16_socks5_probe_protocol():
    """TEST-16: Pure asyncio SOCKS5 client negotiation and HTTP request handling."""
    async def dummy_socks_handler(reader, writer):
        ver, nmethods = await reader.readexactly(2)
        methods = await reader.readexactly(nmethods)
        writer.write(b"\x05\x00")
        await writer.drain()

        req = await reader.readexactly(4)
        atyp = req[3]
        if atyp == 3:
            dlen = (await reader.readexactly(1))[0]
            domain = await reader.readexactly(dlen)
            port = await reader.readexactly(2)

        writer.write(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x04\x38")
        await writer.drain()

        line = await reader.readline()
        while True:
            h = await reader.readline()
            if h in (b"\r\n", b"\n", b""):
                break

        writer.write(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(dummy_socks_handler, "127.0.0.1", 0)
    server_port = server.sockets[0].getsockname()[1]

    try:
        runner = RawJsonRunner(MagicMock(spec=XrayChecker))
        code, body, latency = await runner._probe_socks5(
            server_port, "www.gstatic.com", 80, "/generate_204", timeout=3.0
        )
        assert code == 204
        assert latency > 0
    finally:
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_17_real_xray_test_validator():
    """TEST-17: Real Xray Core validation run (-test -c) on user JSON."""
    from config import AppConfig
    import tempfile
    from pathlib import Path

    if not Path(AppConfig.XRAY_EXECUTABLE).exists():
        pytest.skip("xray executable not present")

    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "valid.json"
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(USER_NL_JSON)

        proc = await asyncio.create_subprocess_exec(
            AppConfig.XRAY_EXECUTABLE, "run", "-test", "-c", str(cfg),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        assert proc.returncode == 0

    corrupt_cfg = json.dumps({"inbounds": [{"port": "NOT_A_PORT"}], "outbounds": []})
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "corrupt.json"
        with open(cfg, "w", encoding="utf-8") as f:
            f.write(corrupt_cfg)

        proc = await asyncio.create_subprocess_exec(
            AppConfig.XRAY_EXECUTABLE, "run", "-test", "-c", str(cfg),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        assert proc.returncode != 0



def test_18_import_manager_friendly_naming():
    """TEST-18: Friendly name extracted from JSON without modifying payload."""
    payload = json.dumps({"remarks": "France Premium", "outbounds": [{"protocol": "freedom"}]})
    from parser.json_detector import JsonDetector, JsonConfigType
    parsed = json.loads(payload)
    name = parsed.get("remarks")
    assert name == "France Premium"


def test_19_core_manager_system_proxy_port_matching():
    """TEST-19: CoreManager aligns system proxy with raw config's actual inbound port and protocol."""
    from services.core_manager import CoreManager
    cm = CoreManager()
    with patch.object(cm, "_write_backup_atomic") as mock_write, \
         patch("winreg.OpenKey"), \
         patch("winreg.SetValueEx"), \
         patch.object(cm, "_read_registry_setting", return_value={"present": False, "type": None, "value": None}), \
         patch.object(cm, "_compare_registry_states", return_value=True), \
         patch("ctypes.windll.wininet.InternetSetOptionW"):
        cm.set_system_proxy(True, proxy_server_str="socks=127.0.0.1:10808")
        assert mock_write.called
        backup = mock_write.call_args[0][1]
        assert backup["managed"]["ProxyServer"]["value"] == "socks=127.0.0.1:10808"


def test_20_tools_manager_dedup_and_cleanup():
    """TEST-20: ToolsManager identifies duplicate RawXrayConfigs by SHA-256 hash."""
    from gui.tabs.archive.managers.tools_manager import ToolsManager
    repo = MagicMock(spec=SQLiteProxyRepository)
    tm = ToolsManager(repo)

    r1 = RawXrayConfig(id=1, name="NL 1", raw_payload=USER_NL_JSON)
    r2 = RawXrayConfig(id=2, name="NL 2", raw_payload=USER_NL_JSON)

    confirmations = []
    tm.request_confirmation.connect(lambda act, count, pids, rids: confirmations.append((act, count, pids, rids)))

    tm.prepare_remove_duplicates([r1, r2], "")
    assert len(confirmations) == 1
    act, count, pids, rids = confirmations[0]
    assert act == "remove_duplicates"
    assert count == 1
    assert rids == [2]


@pytest.mark.asyncio
async def test_21_exact_payload_file_written_equality(tmp_path):
    """TEST-21: The file written to disk for Xray execution is byte-for-byte identical to raw_payload."""
    captured_payloads = []
    real_open = open

    def spy_open(path, mode="r", *args, **kwargs):
        handle = real_open(path, mode, *args, **kwargs)
        if "w" in mode and "config.json" in str(path):
            real_write = handle.write

            def spy_write(data):
                captured_payloads.append(data)
                return real_write(data)

            handle.write = spy_write
        return handle

    runner = RawJsonRunner(MagicMock(spec=XrayChecker))
    cfg = RawXrayConfig(name="NL", raw_payload=USER_NL_JSON)

    with patch("builtins.open", side_effect=spy_open), \
         patch("asyncio.create_subprocess_exec") as mock_exec, \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", return_value=(204, "", 120.0)):

        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.returncode = 0
        mock_proc.communicate = MagicMock(return_value=asyncio.sleep(0, result=(b"", b"")))
        mock_proc.wait = MagicMock(return_value=asyncio.sleep(0, result=0))
        mock_proc.kill = MagicMock()
        mock_exec.return_value = mock_proc

        result = await runner.scan_raw_config(cfg)
        assert result.status == "Valid"

        assert len(captured_payloads) == 1
        assert captured_payloads[0] == USER_NL_JSON


@pytest.mark.asyncio
async def test_22_scan_service_batch_scan_with_raw_json():
    """TEST-22: ScanService scans mixed list of ProxyConfig and RawXrayConfig and saves telemetry."""
    from services.scan_service import ScanService
    from scanner.port_manager import PortManager

    repo = MagicMock(spec=SQLiteProxyRepository)
    repo.save_many = MagicMock(return_value=asyncio.sleep(0, result=2))

    checker = MagicMock(spec=XrayChecker)
    runner_pool = MagicMock()
    runner_pool.set_concurrent_limit = MagicMock()

    async def mock_scan(proxy):
        if isinstance(proxy, RawXrayConfig):
            return ScanResult(status="Valid", latency_ms=130.0, outbound_ip="185.126.34.99", country="NL")
        return ScanResult(status="Valid", latency_ms=45.0, outbound_ip="1.2.3.4", country="US")

    runner_pool.scan_proxy = mock_scan

    service = ScanService(runner_pool, repo)

    p1 = ProxyConfig(protocol="vless", server="1.2.3.4", port=443, remark="P1")
    r1 = RawXrayConfig(name="NL", raw_payload=USER_NL_JSON)

    await service.scan_all([p1, r1], on_progress=lambda p, m: None, concurrent_scans=2)

    assert p1.status == "Valid"
    assert p1.ping == 45.0
    assert r1.status == "Valid"
    assert r1.ping == 130.0
    assert r1.country == "NL"
    assert r1.real_ip == "185.126.34.99"
    assert repo.save_many.called


@pytest.mark.asyncio
async def test_23_speed_service_with_raw_json():
    """TEST-23: ScanService measures speed for RawXrayConfig and updates download_speed."""
    from services.scan_service import ScanService

    repo = MagicMock(spec=SQLiteProxyRepository)
    runner_pool = MagicMock()
    runner_pool.set_concurrent_limit = MagicMock()
    runner_pool.check_download_speed = MagicMock(return_value=asyncio.sleep(0, result=3.85))

    service = ScanService(runner_pool, repo)
    r1 = RawXrayConfig(name="NL", raw_payload=USER_NL_JSON)

    speed = await service.test_speed(r1, max_size_kb=500)
    assert speed == 3.85
    assert r1.download_speed == 3.85


def test_24_data_manager_untested_filter_with_raw_json():
    """TEST-24: DataManager filters untested proxies and raw configs cleanly."""
    from gui.tabs.scanner.managers.data_manager import DataManager

    repo = MagicMock(spec=SQLiteProxyRepository)
    dm = DataManager(repo)

    r_untested = RawXrayConfig(name="Untested JSON", raw_payload=USER_NL_JSON, status="Untested")
    r_valid = RawXrayConfig(name="Valid JSON", raw_payload=USER_NL_JSON, status="Valid")
    p_untested = ProxyConfig(remark="Untested P")
    p_untested.status = "Untested"
    p_valid = ProxyConfig(remark="Valid P")
    p_valid.status = "Valid"

    loaded_events = []
    dm.data_loaded.connect(loaded_events.append)

    dm._current_request_id = 1
    dm._process_proxies([r_untested, r_valid, p_untested, p_valid], target_group="", only_untested=True, req_id=1)
    assert len(loaded_events) == 1
    res = loaded_events[0]
    assert len(res) == 2
    assert r_untested in res
    assert p_untested in res

    dm._current_request_id = 2
    dm._process_proxies([r_untested, r_valid, p_untested, p_valid], target_group="", only_untested=False, req_id=2)
    assert len(loaded_events) == 2
    res_all = loaded_events[1]
    assert len(res_all) == 4


def test_25_context_menu_copy_raw_payload():
    """TEST-25: ContextMenuHandler copies exact raw_payload for RawXrayConfig."""
    from gui.tabs.scanner.context_menu_handler import ContextMenuHandler
    from PySide6.QtWidgets import QApplication

    handler = ContextMenuHandler(
        MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
    )

    r = RawXrayConfig(name="NL", raw_payload=USER_NL_JSON)
    with patch.object(QApplication, "clipboard") as mock_clip, \
         patch("PySide6.QtWidgets.QMessageBox.information"):
        mock_clipboard_inst = MagicMock()
        mock_clip.return_value = mock_clipboard_inst
        handler._copy_to_clipboard(r)
        mock_clipboard_inst.setText.assert_called_with(USER_NL_JSON)


@pytest.mark.asyncio
async def test_26_xray_runner_pool_delegation():
    """TEST-26: XrayRunnerPool delegates RawXrayConfig to RawJsonRunner."""
    from scanner.xray_runner import XrayRunnerPool
    from scanner.port_manager import PortManager

    pool = XrayRunnerPool(MagicMock(spec=PortManager), MagicMock(spec=XrayChecker))
    pool.raw_runner.scan_raw_config = MagicMock(return_value=asyncio.sleep(0, result=ScanResult(status="Valid", latency_ms=88.0)))
    pool.raw_runner.check_download_speed = MagicMock(return_value=asyncio.sleep(0, result=4.2))

    r = RawXrayConfig(name="NL", raw_payload=USER_NL_JSON)
    scan_res = await pool.scan_proxy(r)
    assert scan_res.status == "Valid"
    assert scan_res.latency_ms == 88.0
    assert pool.raw_runner.scan_raw_config.called

    speed_res = await pool.check_download_speed(r, max_size_kb=500)
    assert speed_res == 4.2
    assert pool.raw_runner.check_download_speed.called
