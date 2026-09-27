import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch

from domain.models.raw_config import RawXrayConfig
from domain.proxy import ProxyConfig
from domain.scan_result import ScanResult
from scanner.raw_json_runner import RawJsonRunner
from scanner.checker import XrayChecker
from repository.sqlite_repo import SQLiteProxyRepository
from services.scan_service import ScanService

VALID_NL_JSON = """{
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
      "protocol": "http",
      "settings": {
        "address": "185.126.34.99",
        "level": 8,
        "pass": "@AstroVPN_Official",
        "port": 3128,
        "user": "SDPrqwmPFnjCPHU"
      },
      "tag": "proxy"
    }
  ],
  "remarks": "Netherlands"
}"""


def _create_mock_runner():
    checker = MagicMock(spec=XrayChecker)
    checker.timeout_seconds = 5.0
    return RawJsonRunner(checker)


def _mock_xray_process_lifecycle():
    """Mock process so Xray start/port check succeeds without actually launching xray.exe in unit test."""
    mock_test_proc = MagicMock()
    mock_test_proc.returncode = 0
    mock_test_proc.communicate = MagicMock(return_value=asyncio.sleep(0, result=(b"Configuration OK.", b"")))

    mock_run_proc = MagicMock()
    mock_run_proc.pid = 8888
    mock_run_proc.returncode = None
    mock_run_proc.wait = MagicMock(return_value=asyncio.sleep(0, result=0))
    mock_run_proc.kill = MagicMock()

    return mock_test_proc, mock_run_proc


@pytest.mark.asyncio
async def test_classification_1_valid_config_eof_yields_error_not_invalid():
    """Valid config + EOF (code 0) during probe must result in Error, NEVER Invalid."""
    runner = _create_mock_runner()
    raw_cfg = RawXrayConfig(name="NL", raw_payload=VALID_NL_JSON)

    mock_test_proc, mock_run_proc = _mock_xray_process_lifecycle()

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", return_value=(0, "", 105.0)):

        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Error"
        assert result.status != "Invalid"
        assert "EOF" in result.error_message


@pytest.mark.asyncio
async def test_classification_2_valid_config_connection_failure_yields_error():
    """Valid config + connection failure during probe must result in Error, NEVER Invalid."""
    runner = _create_mock_runner()
    raw_cfg = RawXrayConfig(name="NL", raw_payload=VALID_NL_JSON)

    mock_test_proc, mock_run_proc = _mock_xray_process_lifecycle()

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", side_effect=ConnectionResetError("Connection reset by peer")):

        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Error"
        assert result.status != "Invalid"
        assert "Connection reset by peer" in result.error_message


@pytest.mark.asyncio
async def test_classification_3_valid_config_actual_timeout_yields_timeout():
    """Valid config + actual timeout must result in Timeout."""
    runner = _create_mock_runner()
    raw_cfg = RawXrayConfig(name="NL", raw_payload=VALID_NL_JSON)

    mock_test_proc, mock_run_proc = _mock_xray_process_lifecycle()

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", side_effect=asyncio.TimeoutError()):

        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Timeout"
        assert result.error_message == "Timeout"


@pytest.mark.asyncio
async def test_classification_4_invalid_json_yields_invalid():
    """Corrupt/malformed JSON syntax must result in Invalid."""
    runner = _create_mock_runner()
    raw_cfg = RawXrayConfig(name="Bad JSON", raw_payload="{ corrupt json syntax: missing close bracket")

    result = await runner.scan_raw_config(raw_cfg)

    assert result.status == "Invalid"
    assert "Invalid JSON syntax" in result.error_message


@pytest.mark.asyncio
async def test_classification_5_xray_test_validator_failure_yields_invalid():
    """If xray run -test -c fails due to semantic config error, it must result in Invalid."""
    runner = _create_mock_runner()
    raw_cfg = RawXrayConfig(name="NL", raw_payload=VALID_NL_JSON)

    mock_fail_test_proc = MagicMock()
    mock_fail_test_proc.returncode = 1
    mock_fail_test_proc.communicate = MagicMock(return_value=asyncio.sleep(0, result=(b"", b"Failed to start: invalid routing rule")))

    with patch("asyncio.create_subprocess_exec", return_value=mock_fail_test_proc):
        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Invalid"
        assert "Xray test failed" in result.error_message
        assert "invalid routing rule" in result.error_message


@pytest.mark.asyncio
async def test_classification_6_successful_probe_yields_valid():
    """Successful probe returning HTTP 204 must result in Valid."""
    runner = _create_mock_runner()
    raw_cfg = RawXrayConfig(name="NL", raw_payload=VALID_NL_JSON)

    mock_test_proc, mock_run_proc = _mock_xray_process_lifecycle()

    with patch("asyncio.create_subprocess_exec", side_effect=[mock_test_proc, mock_run_proc]), \
         patch.object(runner, "_wait_for_port", return_value=True), \
         patch.object(runner, "_probe_socks5", side_effect=[
             (204, "", 120.0),
             (200, "ip=185.126.34.99\nloc=NL\n", 80.0)
         ]):

        result = await runner.scan_raw_config(raw_cfg)

        assert result.status == "Valid"
        assert result.latency_ms == 120.0
        assert result.outbound_ip == "185.126.34.99"
        assert result.country == "NL"


@pytest.mark.asyncio
async def test_classification_7_error_message_is_preserved_and_persisted(tmp_path):
    """ScanService must preserve and persist result.error_message onto proxy and database."""
    db_file = str(tmp_path / "test_error_persistence.db")
    repo = SQLiteProxyRepository(db_file)
    await repo.initialize()

    runner_pool = MagicMock()
    runner_pool.set_concurrent_limit = MagicMock()
    runner_pool.checker = MagicMock()
    runner_pool.checker.set_timeout = MagicMock()

    async def mock_scan(proxy):
        return ScanResult(status="Error", error_message="Connection closed (EOF)")

    runner_pool.scan_proxy = mock_scan
    service = ScanService(runner_pool, repo)

    raw_cfg = RawXrayConfig(name="NL JSON", raw_payload=VALID_NL_JSON)
    await repo.save_raw_config(raw_cfg)
    assert raw_cfg.id is not None
    assert raw_cfg.error_message == ""

    await service.scan_all([raw_cfg], on_progress=lambda p, m: None, concurrent_scans=1)

    assert raw_cfg.status == "Error"
    assert raw_cfg.error_message == "Connection closed (EOF)"

    loaded = await repo.get_all_raw_configs()
    assert len(loaded) == 1
    assert loaded[0].status == "Error"
    assert loaded[0].error_message == "Connection closed (EOF)"
