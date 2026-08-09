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

        config = ProxyConfig(
            raw_url=raw_url,
            protocol="vmess",
            remark=str(data.get("ps", "")),
            server=str(data.get("add", "")),
            port=int(data.get("port", 0)),
            uuid_pwd=str(data.get("id", "")),
            sni=str(data.get("sni", "")),
            security=str(data.get("tls", "none")),
            network=str(data.get("net", "tcp")),
            alpn=str(data.get("alpn", "")),
            fingerprint=str(data.get("fp", "")),
            path=str(data.get("path", "")),
            host=str(data.get("host", "")),
        )

        config.aid = str(data.get("aid", "0"))
        config.scy = str(data.get("scy", "auto"))

        self.validate(config)
        return config
