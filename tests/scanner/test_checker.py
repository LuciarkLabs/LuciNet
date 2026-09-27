import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from scanner.checker import XrayChecker

@pytest.fixture
def checker():
    geoip_mock = AsyncMock()
    geoip_mock.get_ip_info.return_value = ("US", "New York", "ISP-X")
    chk = XrayChecker(geoip_mock)
    chk.set_timeout(2)
    return chk

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
async def test_checker_success(checker):
    def mock_get(url, *args, **kwargs):
        if "generate_204" in url:
            return MockResponse(204)
        if "trace" in url:
            return MockResponse(200, "ip=8.8.8.8\nloc=US")
        return MockResponse(200)

    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await checker.check_connection(10800)
        
        assert result.status == "Valid"
        assert result.latency_ms >= 0
        assert result.outbound_ip == "8.8.8.8"
        assert result.country == "US"
        assert result.city == "New York"
        assert result.isp == "ISP-X"

@pytest.mark.asyncio
async def test_checker_http_invalid(checker):
    def mock_get(url, *args, **kwargs):
        return MockResponse(500)

    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await checker.check_connection(10800)
        assert result.status == "Invalid"
        assert "HTTP 500" in result.error_message

@pytest.mark.asyncio
async def test_checker_timeout(checker):
    def mock_get(url, *args, **kwargs):
        raise asyncio.TimeoutError()

    with patch("aiohttp.ClientSession.get", side_effect=mock_get):
        result = await checker.check_connection(10800)
        assert result.status == "Timeout"

