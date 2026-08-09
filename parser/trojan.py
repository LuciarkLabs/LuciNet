from urllib.parse import urlparse, parse_qs, unquote
from domain.proxy import ProxyConfig
from parser.base import BaseParser
from parser.exceptions import ParseError

class TrojanParser(BaseParser):
    def parse(self, raw_url: str) -> ProxyConfig:
        parsed = urlparse(raw_url)
        if parsed.scheme.lower() != "trojan":
            raise ParseError("لینک وارد شده trojan نیست")

        qs = parse_qs(parsed.query)

        def get_qs(key: str, default: str = "") -> str:
            return qs.get(key, [default])[0]

        raw_path = get_qs("path", "/")
        clean_path = unquote(raw_path)

        host = get_qs("host") or get_qs("sni") or parsed.hostname or ""
        sni = get_qs("sni") or host

        config = ProxyConfig(
            raw_url=raw_url,
            protocol="trojan",
            remark=unquote(parsed.fragment),
            server=parsed.hostname or "",
            port=parsed.port or 443,
            uuid_pwd=parsed.username or "",
            sni=sni,
            security=get_qs("security", "tls"),
            network=get_qs("type", "tcp"),
            alpn=get_qs("alpn"),
            path=clean_path,
            host=host,
        )
        self.validate(config)
        return config
