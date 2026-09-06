import json
from parser.base import BaseParser
from domain.proxy import ProxyConfig
from utils.base64_helper import decode_base64
from parser.exceptions import ParseError

class VMessParser(BaseParser):
    def parse(self, raw_url: str) -> ProxyConfig:
        if not raw_url.lower().startswith("vmess://"):
            raise ParseError("پروتکل لینک vmess نیست.")

        b64_str = raw_url[8:]
        try:
            decoded = decode_base64(b64_str)
            data = json.loads(decoded)
        except Exception as e:
            raise ParseError(f"فرمت Base64 یا JSON نامعتبر است: {e}")

        network = str(data.get("net", "tcp")).strip().lower()
        if network == "splithttp":
            network = "xhttp"

        tls_raw = str(data.get("tls", "none")).strip().lower()
        if tls_raw in ("true", "1", "tls"):
            security = "tls"
        elif tls_raw in ("false", "0", "none", ""):
            security = "none"
        else:
            security = tls_raw

        config = ProxyConfig(
            raw_url=raw_url,
            protocol="vmess",
            remark=str(data.get("ps", "")),
            server=str(data.get("add", "")),
            port=int(data.get("port", 0)),
            uuid_pwd=str(data.get("id", "")),
            sni=str(data.get("sni", "")),
            security=security,
            network=network,
            alpn=str(data.get("alpn", "")),
            fingerprint=str(data.get("fp", "")),
            path=str(data.get("path", "")),
            host=str(data.get("host", "")),
        )

        config.aid = str(data.get("aid", "0"))
        config.scy = str(data.get("scy", "auto"))
        config.mode = str(data.get("mode", ""))
        config.extra = str(data.get("extra", ""))

        allow_insecure_str = str(data.get("allowInsecure", "0"))
        insecure_str = str(data.get("insecure", "0"))
        config.allow_insecure = (
            True if (allow_insecure_str == "1" or insecure_str == "1") else False
        )

        self.validate(config)
        return config
