from domain.proxy import ProxyConfig
import ipaddress
import urllib.parse

class XrayConfigValidatorError(Exception):
    pass

class XrayConfigGenerator:

    @staticmethod
    def validate_pre_run(proxy: ProxyConfig):
        if not proxy.server or not proxy.port:
            raise XrayConfigValidatorError("آدرس سرور یا پورت خالی است.")
        if proxy.protocol in ("vless", "vmess", "trojan") and not proxy.uuid_pwd:
            raise XrayConfigValidatorError(
                "برای این پروتکل UUID یا Password الزامی است."
            )
        if proxy.security == "reality" and not getattr(proxy, "pbk", None):
            raise XrayConfigValidatorError(
                "پروتکل Reality نیاز به Public Key (pbk) دارد."
            )

    @staticmethod
    def generate(proxy: ProxyConfig, local_port: int) -> dict:
        XrayConfigGenerator.validate_pre_run(proxy)

        return {
            "log": {
                "loglevel": "none",
            },
            "routing": {
                "rules": [
                    {
                        "type": "field",
                        "inboundTag": ["inbound-local"],
                        "outboundTag": "proxy",
                    }
                ],
            },
            "inbounds": [
                {
                    "tag": "inbound-local",
                    "port": local_port,
                    "listen": "127.0.0.1",
                    "protocol": "mixed",
                    "settings": {"udp": True},

                }
            ],
            "outbounds": [
                XrayConfigGenerator._build_outbound(proxy)

            ],
        }

    @staticmethod
    def _build_outbound(proxy: ProxyConfig) -> dict:
        protocol_name = "shadowsocks" if proxy.protocol == "ss" else proxy.protocol

        return {
            "tag": "proxy",
            "protocol": protocol_name,
            "settings": XrayConfigGenerator._build_settings(proxy),
            "streamSettings": XrayConfigGenerator._build_stream_settings(proxy),
        }

    @staticmethod
    def _build_settings(proxy: ProxyConfig) -> dict:
        if proxy.protocol in ("vless", "vmess"):
            user = {"id": proxy.uuid_pwd}
            if proxy.protocol == "vless":
                user["encryption"] = "none"
                if proxy.flow:
                    user["flow"] = proxy.flow
            else:
                user["alterId"] = int(getattr(proxy, "aid", 0))
                user["security"] = getattr(proxy, "scy", "auto")
            return {
                "vnext": [
                    {"address": proxy.server, "port": int(proxy.port), "users": [user]}
                ]
            }

        elif proxy.protocol in ("trojan", "ss"):
            server = {
                "address": proxy.server,
                "port": proxy.port,
            }

            if proxy.protocol == "ss":
                if ":" in proxy.uuid_pwd:
                    method, pwd = proxy.uuid_pwd.split(":", 1)
                    server["method"] = method
                    server["password"] = pwd
                else:
                    server["method"] = "aes-256-gcm"
                    server["password"] = proxy.uuid_pwd
            else:
                server["password"] = proxy.uuid_pwd

            return {"servers": [server]}

    @staticmethod
    def _build_stream_settings(proxy: ProxyConfig) -> dict:
        stream = {
            "network": proxy.network if proxy.network else "tcp",
            "security": proxy.security if proxy.security else "none",
        }

        valid_domain = proxy.sni if proxy.sni else (proxy.host if proxy.host else "")
        if not valid_domain:
            try:
                ipaddress.ip_address(proxy.server)
            except ValueError:
                valid_domain = proxy.server

        if proxy.network == "ws":
            raw_path = proxy.path if proxy.path else "/"
            clean_path = urllib.parse.unquote(raw_path)
            if not clean_path.startswith("/"):
                clean_path = "/" + clean_path

            ws_settings = {"path": clean_path}

            host_header = proxy.host if proxy.host else valid_domain
            if host_header:
                ws_settings["headers"] = {"Host": host_header}

            stream["wsSettings"] = ws_settings

        elif proxy.network == "grpc":
            stream["grpcSettings"] = {
                "serviceName": proxy.path if proxy.path else "",
                "multiMode": False,
            }

        elif proxy.network == "httpupgrade":
            stream["httpupgradeSettings"] = {
                "path": proxy.path if proxy.path else "/",
                "host": proxy.host if proxy.host else "",
            }

        if proxy.security == "tls":
            server_name = valid_domain

            try:
                ipaddress.ip_address(server_name)
                server_name = ""
            except ValueError:
                pass

            stream["tlsSettings"] = {
                "serverName": server_name,
                "fingerprint": proxy.fingerprint if proxy.fingerprint else "chrome",
            }
            if proxy.alpn:
                stream["tlsSettings"]["alpn"] = [
                    a.strip() for a in proxy.alpn.split(",")
                ]

        elif proxy.security == "reality":
            stream["realitySettings"] = {
                "serverName": proxy.sni if proxy.sni else proxy.server,
                "fingerprint": proxy.fingerprint if proxy.fingerprint else "chrome",
                "publicKey": proxy.pbk if proxy.pbk else "",
                "shortId": proxy.sid if proxy.sid else "",
                "spiderX": proxy.spx if proxy.spx else "/",
            }

        return stream
