import re
from urllib.parse import urlparse, unquote
from parser.base import BaseParser
from domain.proxy import ProxyConfig
from utils.base64_helper import decode_base64
from parser.exceptions import ParseError

class ShadowsocksParser(BaseParser):
    def parse(self, raw_url: str) -> ProxyConfig:
        if not raw_url.lower().startswith("ss://"):
            raise ParseError("لینک shadowsocks نامعتبر است")

        parsed = urlparse(raw_url)
        remark = unquote(parsed.fragment)

        server = ""
        port = 0
        method_password = ""

        try:

            server = parsed.hostname
            port = parsed.port
            method_password = parsed.username
        except ValueError:

            pass

        if not server or not port:

            core_part = raw_url[5:].split("#")[0]

            if "@" in core_part:

                part1, part2 = core_part.rsplit("@", 1)
                method_password = part1

                if ":" in part2:
                    server_part, port_part = part2.rsplit(":", 1)
                    server = server_part

                    port_match = re.search(r"^(\d+)", port_part)
                    if port_match:
                        port = int(port_match.group(1))

                        if not remark and len(port_part) > len(port_match.group(1)):
                            extra = unquote(port_part[len(port_match.group(1)) :])
                            if extra.startswith("@"):
                                extra = extra[1:]
                            remark = extra.strip()
            else:

                try:
                    decoded = decode_base64(core_part)
                    if "@" in decoded:
                        part1, part2 = decoded.rsplit("@", 1)
                        method_password = part1
                        if ":" in part2:
                            server_part, port_part = part2.rsplit(":", 1)
                            server = server_part
                            port_match = re.search(r"^(\d+)", port_part)
                            if port_match:
                                port = int(port_match.group(1))
                except Exception as e:
                    raise ParseError(f"خطا در دیکد SS: {e}")

        if method_password and ":" not in method_password:
            try:
                method_password = decode_base64(method_password)
            except:
                pass

        config = ProxyConfig(
            raw_url=raw_url,
            protocol="ss",
            remark=remark or "Shadowsocks",
            server=server or "",
            port=port or 0,
            uuid_pwd=method_password or "",
            network="tcp",
            security="none",
        )
        self.validate(config)
        return config
