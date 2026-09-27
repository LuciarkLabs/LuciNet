import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Any, Dict, List
from utils.url_normalizer import normalize_config_url
from .transport import TransportConfig
from .security import TLSConfig, RealityConfig
from .outbound import MuxConfig, OutboundOptions
from .metadata import ParseMetadata, ProxyRuntime, ProxyStorage

@dataclass(eq=False)
class ProxyConfig:
    raw_url: str = field(default="", repr=False)
    protocol: str = ""
    remark: str = ""
    server: str = ""
    port: int = 0

    user_id: str = field(default="", repr=False)
    password: str = field(default="", repr=False)
    method: str = ""
    email: str = ""
    level: int = 0

    encryption: str = ""
    flow: str = ""
    vmess_aid: str = "0"
    vmess_scy: str = "auto"
    vmess_experiments: str = ""
    vless_reverse: Optional[Dict[str, Any]] = None
    udp: Optional[bool] = None
    ss_uot: Optional[bool] = None

    transport: TransportConfig = field(default_factory=TransportConfig)

    security_type: str = "none"
    tls: TLSConfig = field(default_factory=TLSConfig)
    reality: RealityConfig = field(default_factory=RealityConfig)

    finalmask_raw: str = ""
    finalmask: Optional[Dict[str, Any]] = None
    sockopt: Optional[Dict[str, Any]] = None
    outbound: OutboundOptions = field(default_factory=OutboundOptions)

    parse_meta: ParseMetadata = field(default_factory=ParseMetadata)

    runtime: ProxyRuntime = field(default_factory=ProxyRuntime)
    storage: ProxyStorage = field(default_factory=ProxyStorage)


    @property
    def source_format(self):
        return self.parse_meta.source_format

    @source_format.setter
    def source_format(self, value):
        self.parse_meta.source_format = value

    @property
    def extensions(self):
        return self.parse_meta.extensions

    @extensions.setter
    def extensions(self, value):
        self.parse_meta.extensions = value

    @property
    def unknown_params(self):
        return self.parse_meta.unknown_params

    @unknown_params.setter
    def unknown_params(self, value):
        self.parse_meta.unknown_params = value

    @property
    def warnings(self):
        return self.parse_meta.warnings

    @warnings.setter
    def warnings(self, value):
        self.parse_meta.warnings = value

    @property
    def id(self):
        return self.storage.id

    @id.setter
    def id(self, value):
        self.storage.id = value

    @property
    def sub_id(self):
        return self.storage.sub_id

    @sub_id.setter
    def sub_id(self, value):
        self.storage.sub_id = value

    @property
    def group_name(self):
        return self.storage.group_name

    @group_name.setter
    def group_name(self, value):
        self.storage.group_name = value

    @property
    def status(self):
        return self.runtime.status

    @status.setter
    def status(self, value):
        self.runtime.status = value

    @property
    def ping(self):
        return self.runtime.ping if self.runtime.ping is not None else -1.0

    @ping.setter
    def ping(self, value):
        self.runtime.ping = value

    @property
    def download_speed(self):
        return (
            self.runtime.download_speed
            if self.runtime.download_speed is not None
            else 0.0
        )

    @download_speed.setter
    def download_speed(self, value):
        self.runtime.download_speed = value

    @property
    def country(self):
        return self.runtime.country

    @country.setter
    def country(self, value):
        self.runtime.country = value

    @property
    def city(self):
        return self.runtime.city

    @city.setter
    def city(self, value):
        self.runtime.city = value

    @property
    def isp(self):
        return self.runtime.isp

    @isp.setter
    def isp(self, value):
        self.runtime.isp = value

    @property
    def real_ip(self):
        return self.runtime.real_ip

    @real_ip.setter
    def real_ip(self, value):
        self.runtime.real_ip = value

    @property
    def first_seen(self):
        return self.storage.first_seen

    @first_seen.setter
    def first_seen(self, value):
        self.storage.first_seen = value

    @property
    def last_scan(self):
        return self.storage.last_scan

    @last_scan.setter
    def last_scan(self, value):
        self.storage.last_scan = value

    @property
    def last_seen_alive(self):
        return self.storage.last_seen_alive

    @last_seen_alive.setter
    def last_seen_alive(self, value):
        self.storage.last_seen_alive = value

    @property
    def scan_count(self):
        return self.storage.scan_count

    @scan_count.setter
    def scan_count(self, value):
        self.storage.scan_count = value

    @property
    def uuid_pwd(self):
        if self.protocol.lower() in ("ss", "shadowsocks"):
            return f"{self.method}:{self.password}" if self.password else self.method
        return self.user_id or self.password or self.method

    @uuid_pwd.setter
    def uuid_pwd(self, value):
        protocol_lower = self.protocol.lower()
        if protocol_lower in ("vless", "vmess"):
            self.user_id = value
        elif protocol_lower == "trojan":
            self.password = value
        elif protocol_lower in ("ss", "shadowsocks"):
            if ":" in value:
                self.method, self.password = value.split(":", 1)
            else:
                self.method = value
                self.password = ""

    @property
    def network(self):
        return self.transport.network

    @network.setter
    def network(self, value):
        self.transport.network = value

    @property
    def security(self):
        return self.security_type

    @security.setter
    def security(self, value):
        self.security_type = value

    @property
    def sni(self):
        return self.tls.server_name

    @sni.setter
    def sni(self, value):
        self.tls.server_name = value

    @property
    def alpn(self):
        return ",".join(self.tls.alpn) if self.tls.alpn else ""

    @alpn.setter
    def alpn(self, value):
        self.tls.alpn = [item.strip() for item in value.split(",") if item.strip()] if value else []

    @property
    def fingerprint(self):
        return self.tls.fingerprint

    @fingerprint.setter
    def fingerprint(self, value):
        self.tls.fingerprint = value

    @property
    def path(self):
        return self.transport.path

    @path.setter
    def path(self, value):
        self.transport.path = value

    @property
    def host(self):
        return self.transport.host

    @host.setter
    def host(self, value):
        self.transport.host = value

    @property
    def pbk(self):
        return self.reality.password

    @pbk.setter
    def pbk(self, value):
        self.reality.password = value

    @property
    def sid(self):
        return self.reality.short_id

    @sid.setter
    def sid(self, value):
        self.reality.short_id = value

    @property
    def spx(self):
        return self.reality.spider_x

    @spx.setter
    def spx(self, value):
        self.reality.spider_x = value

    @property
    def allow_insecure(self):
        return self.tls.allow_insecure

    @allow_insecure.setter
    def allow_insecure(self, value):
        self.tls.allow_insecure = value

    @property
    def mode(self):
        if self.transport.network == "grpc":
            return self.transport.grpc_mode
        if self.transport.network == "xhttp":
            return self.transport.xhttp_mode
        return ""

    @mode.setter
    def mode(self, value):
        if self.transport.network == "grpc":
            self.transport.grpc_mode = value
        elif self.transport.network == "xhttp":
            self.transport.xhttp_mode = value

    @property
    def aid(self):
        return self.vmess_aid

    @aid.setter
    def aid(self, value):
        self.vmess_aid = str(value)

    @property
    def scy(self):
        return self.vmess_scy

    @scy.setter
    def scy(self, value):
        self.vmess_scy = str(value)

    @property
    def extra(self):
        return self.transport.xhttp_extra

    @extra.setter
    def extra(self, value):
        self.transport.xhttp_extra = value

    @property
    def source_hash(self) -> str:
        """تولید هش بر اساس URL نرمال‌شده (همان unique_hash قبلی)"""
        normalized = normalize_config_url(self.raw_url)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @property
    def unique_hash(self) -> str:
        return self.source_hash

    @property
    def connection_hash(self) -> str:
        """
        تولید هش هویتی نود (Endpoint Identity Hash).
        صرفاً برای پیدا کردن سرورهای دقیقاً مشابه (فارغ از تنظیمات transport/security).
        """
        norm_protocol = self.protocol.lower()
        if norm_protocol == "ss":
            norm_protocol = "shadowsocks"
        payload = {
            "protocol": norm_protocol,
            "server": self.server,
            "port": self.port,
            "user_id": self.user_id,
            "password": self.password,
            "method": self.method,
        }
        json_str = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    @property
    def config_hash(self) -> str:
        """
        تولید هش پیکربندی (Configuration Hash).
        فقط فیلدهای موثر در اتصال بر اساس نوع شبکه و امنیت هش می‌شوند.
        """
        norm_protocol = self.protocol.lower()
        if norm_protocol == "ss":
            norm_protocol = "shadowsocks"
        
        outbound_dict = asdict(self.outbound)
        if self.outbound.mux and not self.outbound.mux.enabled:
            outbound_dict["mux"] = None
        elif not self.outbound.mux:
            outbound_dict["mux"] = None
            
        payload = {
            "protocol": norm_protocol,
            "server": self.server,
            "port": self.port,
            "user_id": self.user_id,
            "password": self.password,
            "method": self.method,
            "encryption": self.encryption,
            "flow": self.flow,
            "level": self.level,
            "email": self.email,
            "udp": self.udp,
            "ss_uot": self.ss_uot,
            "vless_reverse": self.vless_reverse,
            "vmess_aid": self.vmess_aid,
            "vmess_scy": self.vmess_scy,
            "vmess_experiments": self.vmess_experiments,
            "security": self.security_type.lower(),
            "outbound": outbound_dict,
        }

        t_dict = asdict(self.transport)
        net = self.transport.network.lower()
        if net == "tcp": net = "raw"
        elif net == "ws": net = "websocket"
        elif net == "kcp": net = "mkcp"
        elif net == "splithttp": net = "xhttp"
        
        e_t = {"network": net}
        if net == "websocket":
            e_t.update({k: v for k, v in t_dict.items() if k.startswith("ws_") or k in ("path", "host")})
        elif net == "grpc":
            e_t.update({k: v for k, v in t_dict.items() if k.startswith("grpc_")})
        elif net == "xhttp":
            e_t.update({k: v for k, v in t_dict.items() if k.startswith("xhttp_") or k in ("path", "host")})
        elif net == "mkcp":
            e_t.update({k: v for k, v in t_dict.items() if k.startswith("kcp_")})
        elif net == "httpupgrade":
            e_t.update({k: v for k, v in t_dict.items() if k.startswith("httpupgrade_") or k in ("path", "host")})
        elif net == "hysteria":
            e_t["hysteria"] = str(t_dict.get("hysteria", ""))
        elif net == "raw":
            e_t["raw_header"] = str(t_dict.get("raw_header", ""))
        payload["transport"] = e_t

        norm_sec = self.security_type.lower()
        if norm_sec == "tls":
            payload["tls"] = asdict(self.tls)
        elif norm_sec == "reality":
            payload["reality"] = asdict(self.reality)

        if self.finalmask:
            payload["finalmask"] = self.finalmask
        elif self.finalmask_raw:
            try:
                payload["finalmask"] = json.loads(self.finalmask_raw)
            except Exception:
                payload["finalmask"] = self.finalmask_raw

        if self.sockopt:
            payload["sockopt"] = self.sockopt

        json_str = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

