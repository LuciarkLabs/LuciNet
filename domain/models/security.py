from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class TLSConfig:
    server_name: str = ""
    verify_peer_cert_by_name: str = ""
    allow_insecure: bool = False
    alpn: List[str] = field(default_factory=list)
    min_version: str = ""
    max_version: str = ""
    cipher_suites: str = ""
    disable_system_root: bool = False
    enable_session_resumption: bool = False
    fingerprint: str = ""
    pinned_peer_cert_sha256: str = ""
    curve_preferences: List[str] = field(default_factory=list)
    master_key_log: str = field(default="", repr=False)
    ech_config_list: str = ""
    ech_sockopt: Dict[str, Any] = field(default_factory=dict)
    certificates: List[Dict[str, Any]] = field(default_factory=list, repr=False)



@dataclass
class RealityConfig:
    password: str = field(default="", repr=False)
    short_id: str = ""
    spider_x: str = ""
    mldsa65_verify: str = ""

    @property
    def public_key(self):
        return self.password

    @public_key.setter
    def public_key(self, value):
        self.password = value



