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

        def get_query_value(query: str, key: str, default: str = "") -> str:
            for part in query.split("&"):
                if not part:
                    continue
                k, _, v = part.partition("=")
                if k == key:
                    return unquote(v)
            return default

        path = get_query_value(parsed.query, "path", "")
        explicit_host = get_query_value(parsed.query, "host", "")
        host = explicit_host
        sni = (
            get_query_value(parsed.query, "sni", "")
            or explicit_host
            or parsed.hostname
            or ""
        )

        mode = get_query_value(parsed.query, "mode", "")
        extra = get_query_value(parsed.query, "extra", "")

        allow_insecure_str = get_qs("allowInsecure", "0")
        insecure_str = get_qs("insecure", "0")
        allow_insecure = (
            True if (allow_insecure_str == "1" or insecure_str == "1") else False
        )

        network = get_qs("type", "tcp").strip().lower()
        if network == "splithttp":
            network = "xhttp"

        config = ProxyConfig(
            raw_url=raw_url,
            protocol="trojan",
            remark=unquote(parsed.fragment),
            server=parsed.hostname or "",
            port=parsed.port or 443,
            uuid_pwd=parsed.username or "",
            sni=sni,
            security=get_qs("security", "tls"),
            network=network,
            alpn=get_qs("alpn"),
            path=path,
            host=host,
            mode=mode,
            extra=extra,
            allow_insecure=allow_insecure,
        )
        self.validate(config)
        return config
