from urllib.parse import urlparse, parse_qs, unquote
from domain.proxy import ProxyConfig
from parser.base import BaseParser
from parser.exceptions import ParseError

class VlessParser(BaseParser):
    def parse(self, raw_url: str) -> ProxyConfig:
        parsed = urlparse(raw_url)
        if parsed.scheme.lower() != "vless":
            raise ParseError("لینک وارد شده vless نیست")

        qs = parse_qs(parsed.query)
        def get_qs(key: str, default: str = "") -> str:
            return qs.get(key, [default])[0]

        raw_path = get_qs("path", "/")
        clean_path = unquote(raw_path)

        host = get_qs("host") or get_qs("sni") or parsed.hostname or ""
        sni = get_qs("sni") or host

        config = ProxyConfig(
            raw_url=raw_url,
            protocol="vless",
            remark=unquote(parsed.fragment),
            server=parsed.hostname or "",
            port=parsed.port or 443,
            uuid_pwd=parsed.username or "",
            sni=sni,
            security=get_qs("security", "none"),
            network=get_qs("type", "tcp"),
            flow=get_qs("flow"),
            alpn=get_qs("alpn"),
            fingerprint=get_qs("fp"),
            path=clean_path,
            host=host,
            pbk=get_qs("pbk"),
            sid=get_qs("sid"),
            spx=get_qs("spx"),
        )
        self.validate(config)
        return config
