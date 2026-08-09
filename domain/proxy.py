import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional
from utils.url_normalizer import normalize_config_url

@dataclass
class ProxyConfig:
    raw_url: str
    protocol: str = ""
    remark: str = ""
    server: str = ""
    port: int = 0

    uuid_pwd: str = ""
    sni: str = ""
    security: str = ""
    network: str = ""
    flow: str = ""
    alpn: str = ""
    fingerprint: str = ""
    path: str = ""
    host: str = ""
    pbk: str = ""
    sid: str = ""
    spx: str = ""

    country: str = ""
    city: str = ""
    isp: str = ""
    ping: float = -1.0
    download_speed: float = 0.0
    status: str = "Untested"
    group_name: str = "Default"
    first_seen: float = field(default_factory=time.time)
    last_scan: float = 0.0
    last_seen_alive: float = 0.0
    scan_count: int = 0

    id: Optional[int] = None

    @property
    def unique_hash(self) -> str:
        normalized = normalize_config_url(self.raw_url)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
