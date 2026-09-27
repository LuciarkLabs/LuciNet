import json
import base64
import ipaddress
import urllib.parse
from domain.proxy import ProxyConfig


class ClientConfigGenerator:
    """موتور تولید فایل JSON استاندارد Xray برای کلاینت اصلی (نسخه گلوبال)"""

    @staticmethod
    def _is_ip(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except Exception:
            return False

    @staticmethod
    def _normalize_network(network: str) -> str:
        net = (network or "tcp").strip().lower()
        if net in ("websocket", "ws"):
            return "ws"
        if net in ("raw", "tcp"):
            return "tcp"
        if net in ("splithttp", "xhttp"):
            return "xhttp"
        if net in ("mkcp", "kcp"):
            return "kcp"
        return net

    @staticmethod
    def _fallback_domain(proxy: ProxyConfig) -> str:
        values = [
            getattr(proxy, "sni", "") or "",
            getattr(proxy, "host", "") or "",
            proxy.server or "",
        ]

        for value in values:
            value = value.strip()
            if value and not ClientConfigGenerator._is_ip(value):
                return value

        return ""

    @staticmethod
    def _parse_xhttp_extra(extra_raw: str):
        if not extra_raw:
            return None

        s = urllib.parse.unquote(str(extra_raw)).strip()
        if not s:
            return None

        if s.startswith("{"):
            try:
                return json.loads(s)
            except Exception:
                return None

        candidates = [s, s.replace("-", "+").replace("_", "/")]

        for candidate in candidates:
            try:
                pad = "=" * (-len(candidate) % 4)
                decoded = base64.b64decode(candidate + pad).decode("utf-8")
                return json.loads(decoded)
            except Exception:
                continue

        return None

    @staticmethod
    def validate_pre_run(proxy: ProxyConfig):
        if not proxy.server or not proxy.port:
            raise ValueError("آدرس سرور یا پورت خالی است.")
        if proxy.protocol in ("vless", "vmess", "trojan") and not proxy.uuid_pwd:
            raise ValueError("برای این پروتکل UUID یا Password الزامی است.")
        if proxy.security == "reality" and not getattr(proxy, "pbk", None):
            raise ValueError("پروتکل Reality نیاز به Public Key (pbk) دارد.")

    @staticmethod
    def generate(proxy: ProxyConfig, local_port: int, enable_tun: bool = False) -> dict:
        ClientConfigGenerator.validate_pre_run(proxy)

        inbounds = [
            {
                "tag": "inbound-local",
                "port": local_port,
                "listen": "127.0.0.1",
                "protocol": "mixed",
                "settings": {"udp": True},
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                    "routeOnly": True,
                },
            }
        ]

        if enable_tun:
            inbounds.append(
                {
                    "tag": "tun-in",
                    "protocol": "tun",
                    "settings": {
                        "name": "LuciNet",
                        "MTU": 1500,
                        "gateway": ["172.18.0.1/30", "fdfe:dcba:9876::1/126"],
                        "autoSystemRoutingTable": ["0.0.0.0/0", "::/0"],
                        "autoOutboundsInterface": "auto",
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": [
                            "http",
                            "tls",
                            "quic",
                        ],
                        "routeOnly": True,
                    },
                }
            )

        outbounds = [
            ClientConfigGenerator._build_outbound(proxy),
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"},
        ]

        if enable_tun:
            outbounds.append({"protocol": "dns", "tag": "dns-out"})

        config_dict = {
            "log": {"loglevel": "info"},
            "inbounds": inbounds,
            "outbounds": outbounds,
        }

        if enable_tun:
            config_dict["dns"] = {
                "servers": [
                    "https://dns.google/dns-query",
                    "https://1.1.1.1/dns-query",
                    "8.8.8.8",
                    "1.1.1.1",
                ],
                "queryStrategy": "UseIPv4",
            }

            rules = [
                {
                    "type": "field",
                    "inboundTag": ["tun-in"],
                    "port": "135,137,138,139,1900,5353",
                    "network": "udp",
                    "outboundTag": "block",
                },
                {
                    "type": "field",
                    "port": 53,
                    "network": "udp",
                    "inboundTag": ["tun-in"],
                    "outboundTag": "dns-out",
                },
                {
                    "type": "field",
                    "port": 53,
                    "network": "udp",
                    "ip": ["8.8.8.8", "1.1.1.1"],
                    "outboundTag": "proxy",
                },
                {
                    "type": "field",
                    "network": "udp",
                    "port": 443,
                    "outboundTag": "block",
                },
                {
                    "type": "field",
                    "domain": [
                        "dns.google",
                        "dns.google.com",
                        "cloudflare-dns.com",
                        "mozilla.cloudflare-dns.com",
                    ],
                    "outboundTag": "proxy",
                },
            ]

            direct_ips = [
                "192.168.0.0/16",
                "10.0.0.0/8",
                "172.16.0.0/12",
                "127.0.0.0/8",
            ]
            direct_domains = []

            if ClientConfigGenerator._is_ip(proxy.server):
                direct_ips.append(proxy.server)
            else:
                direct_domains.append(proxy.server)

            if direct_ips:
                rules.append(
                    {
                        "type": "field",
                        "outboundTag": "direct",
                        "ip": direct_ips,
                    }
                )

            if direct_domains:
                rules.append(
                    {
                        "type": "field",
                        "outboundTag": "direct",
                        "domain": direct_domains,
                    }
                )

            rules.append(
                {
                    "type": "field",
                    "inboundTag": ["tun-in", "inbound-local"],
                    "outboundTag": "proxy",
                }
            )

            config_dict["routing"] = {"domainStrategy": "IPIfNonMatch", "rules": rules}

        return config_dict

    @staticmethod
    def _build_outbound(proxy: ProxyConfig) -> dict:
        proto = (proxy.protocol or "").strip().lower()
        protocol_name = "shadowsocks" if proto in ("ss", "shadowsocks") else proto

        return {
            "tag": "proxy",
            "protocol": protocol_name,
            "settings": ClientConfigGenerator._build_settings(proxy),
            "streamSettings": ClientConfigGenerator._build_stream_settings(proxy),
        }

    @staticmethod
    def _build_settings(proxy: ProxyConfig) -> dict:
        proto = (proxy.protocol or "").strip().lower()
        if proto in ("vless", "vmess"):
            user = {"id": proxy.uuid_pwd}

            if proto == "vless":
                user["encryption"] = "none"
                flow = getattr(proxy, "flow", "")
                if flow:
                    user["flow"] = flow
            else:
                alter_id = getattr(proxy, "vmess_aid", getattr(proxy, "aid", 0))
                user["alterId"] = int(alter_id) if str(alter_id).isdigit() else 0
                user["security"] = getattr(proxy, "vmess_scy", getattr(proxy, "scy", "auto")) or "auto"

            return {
                "vnext": [
                    {"address": proxy.server, "port": int(proxy.port), "users": [user]}
                ]
            }

        elif proto in ("trojan", "ss", "shadowsocks"):
            server = {
                "address": proxy.server,
                "port": int(proxy.port),
            }

            if proto in ("ss", "shadowsocks"):
                if ":" in proxy.uuid_pwd:
                    method, pwd = proxy.uuid_pwd.split(":", 1)
                    server["method"] = method
                    server["password"] = pwd
                else:
                    server["method"] = getattr(proxy, "method", "") or "aes-256-gcm"
                    server["password"] = getattr(proxy, "password", "") or proxy.uuid_pwd
            else:
                server["password"] = proxy.uuid_pwd

            return {"servers": [server]}

    @staticmethod
    def _build_stream_settings(proxy: ProxyConfig) -> dict:
        network = ClientConfigGenerator._normalize_network(proxy.network)

        stream = {
            "network": network,
            "security": proxy.security if proxy.security else "none",
        }

        valid_domain = proxy.sni if proxy.sni else (proxy.host if proxy.host else "")
        if not valid_domain and not ClientConfigGenerator._is_ip(proxy.server):
            valid_domain = proxy.server

        if network in ("ws", "websocket"):
            raw_path = proxy.path if proxy.path else "/"
            clean_path = urllib.parse.unquote(raw_path)
            if not clean_path.startswith("/"):
                clean_path = "/" + clean_path

            ws_settings = {"path": clean_path}
            host_header = proxy.host if proxy.host else valid_domain
            if host_header:
                ws_settings["headers"] = {"Host": host_header}

            stream["wsSettings"] = ws_settings

        elif network == "grpc":
            stream["grpcSettings"] = {
                "serviceName": proxy.path if proxy.path else "",
                "multiMode": False,
            }

        elif network == "httpupgrade":
            stream["httpupgradeSettings"] = {
                "path": proxy.path if proxy.path else "/",
                "host": proxy.host if proxy.host else "",
            }

        elif network == "xhttp":
            xhttp_settings = {}
            fallback_domain = ClientConfigGenerator._fallback_domain(proxy)

            path = (getattr(proxy, "path", "") or "").strip()
            if not path:
                path = "/"
            if not path.startswith("/"):
                path = "/" + path
            xhttp_settings["path"] = path

            host = (getattr(proxy, "host", "") or "").strip()
            if not host:
                host = fallback_domain
            if host and not ClientConfigGenerator._is_ip(host):
                xhttp_settings["host"] = host

            mode = (getattr(proxy, "mode", "") or "").strip()
            if not mode or mode == "auto":
                if "stream-up" in path:
                    mode = "stream-up"
                elif "packet-up" in path:
                    mode = "packet-up"
                elif "stream-one" in path:
                    mode = "stream-one"
                else:
                    mode = "auto"

            xhttp_settings["mode"] = mode

            extra_dict = ClientConfigGenerator._parse_xhttp_extra(
                getattr(proxy, "extra", "")
            )
            if extra_dict:
                xhttp_settings["extra"] = extra_dict
            elif getattr(proxy, "extra", ""):
                print(f"[Warning] Failed to parse xhttp extra: {proxy.extra}")

            stream["xhttpSettings"] = xhttp_settings

        if proxy.security == "tls":
            fallback_domain = ClientConfigGenerator._fallback_domain(proxy)
            server_name = (proxy.sni or proxy.host or "").strip()

            if not server_name or ClientConfigGenerator._is_ip(server_name):
                server_name = fallback_domain

            tls_settings = {
                "allowInsecure": bool(getattr(proxy, "allow_insecure", False)),
                "fingerprint": getattr(proxy, "fingerprint", "") or "chrome",
            }

            if server_name and not ClientConfigGenerator._is_ip(server_name):
                tls_settings["serverName"] = server_name

            if proxy.alpn:
                alpn_list = [a.strip() for a in proxy.alpn.split(",") if a.strip()]
                if alpn_list:
                    tls_settings["alpn"] = alpn_list
            elif network == "xhttp":
                tls_settings["alpn"] = ["h2", "http/1.1"]

            stream["tlsSettings"] = tls_settings

        elif proxy.security == "reality":
            server_name = (proxy.sni or proxy.host or "").strip()

            reality_settings = {
                "publicKey": proxy.pbk if proxy.pbk else "",
                "shortId": proxy.sid if proxy.sid else "",
                "spiderX": (
                    getattr(proxy, "spx", "") if getattr(proxy, "spx", None) else ""
                ),
                "fingerprint": getattr(proxy, "fingerprint", "") or "chrome",
            }

            if server_name and not ClientConfigGenerator._is_ip(server_name):
                reality_settings["serverName"] = server_name
            elif not ClientConfigGenerator._is_ip(proxy.server):
                reality_settings["serverName"] = proxy.server

            stream["realitySettings"] = reality_settings

        return stream
