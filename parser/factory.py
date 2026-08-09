from domain.proxy import ProxyConfig
from parser.vless import VlessParser
from parser.trojan import TrojanParser
from parser.vmess import VMessParser
from parser.shadowsocks import ShadowsocksParser
from parser.exceptions import ParseError, UnsupportedProtocolError

class ParserFactory:
    def __init__(self):
        self._parsers = {
            "vless": VlessParser(),
            "trojan": TrojanParser(),
            "vmess": VMessParser(),
            "ss": ShadowsocksParser(),
        }

    def parse_url(self, raw_url: str) -> ProxyConfig:
        raw_url = raw_url.strip()
        if "://" not in raw_url:
            raise ParseError("فرمت لینک نامعتبر است (отсутствует ://)")

        protocol = raw_url.split("://")[0].lower()
        if protocol == "shadowsocks":
            protocol = "ss"

        parser = self._parsers.get(protocol)
        if not parser:
            raise UnsupportedProtocolError(f"پروتکل پشتیبانی نمی‌شود: {protocol}")

        return parser.parse(raw_url)
