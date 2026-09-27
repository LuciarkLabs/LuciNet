from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import time
import hashlib
import json


@dataclass(eq=False)
class RawXrayConfig:
    id: Optional[int] = None
    name: str = ""
    raw_payload: str = field(default="", repr=False)
    group_name: str = "Default"
    source_type: str = "import"
    source_ref: str = ""
    sub_id: Optional[int] = None
    created_at: float = field(default_factory=time.time)

    status: str = "Untested"
    ping: float = -1.0
    download_speed: float = 0.0
    country: str = ""
    city: str = ""
    isp: str = ""
    real_ip: str = ""
    last_scan: float = 0.0
    last_seen_alive: float = 0.0
    scan_count: int = 0
    error_message: str = ""


    @property
    def remark(self) -> str:
        return self.name

    @remark.setter
    def remark(self, value: str):
        self.name = value

    @property
    def protocol(self) -> str:
        return "raw json"

    @property
    def is_raw(self) -> bool:
        return True

    @property
    def raw_url(self) -> str:
        return ""

    @property
    def source_hash(self) -> str:
        """SHA-256 hash of the exact raw payload bytes (strictly immutable)."""
        return hashlib.sha256(self.raw_payload.encode("utf-8")).hexdigest()

    @property
    def unique_hash(self) -> str:
        return self.source_hash


    def _get_primary_outbound(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.raw_payload)
            for ob in data.get("outbounds", []):
                if not isinstance(ob, dict):
                    continue
                prot = ob.get("protocol", "").lower()
                if prot in ("freedom", "blackhole", "dns"):
                    continue
                return ob
        except Exception:
            pass
        return {}

    @property
    def network(self) -> str:
        ob = self._get_primary_outbound()
        if ob:
            stream = ob.get("streamSettings", {})
            if isinstance(stream, dict):
                return stream.get("network", "")
        return ""

    @property
    def security(self) -> str:
        ob = self._get_primary_outbound()
        if ob:
            stream = ob.get("streamSettings", {})
            if isinstance(stream, dict):
                return stream.get("security", "")
        return ""

    @property
    def server(self) -> str:
        ob = self._get_primary_outbound()
        if not ob:
            return ""
        settings = ob.get("settings", {})
        if not isinstance(settings, dict):
            return ""
        if "vnext" in settings and isinstance(settings["vnext"], list) and settings["vnext"]:
            return settings["vnext"][0].get("address", "")
        if "servers" in settings and isinstance(settings["servers"], list) and settings["servers"]:
            return settings["servers"][0].get("address", "")
        if "address" in settings:
            return str(settings["address"])
        return ""

    @property
    def port(self) -> int:
        ob = self._get_primary_outbound()
        if not ob:
            return 0
        settings = ob.get("settings", {})
        if not isinstance(settings, dict):
            return 0
        if "vnext" in settings and isinstance(settings["vnext"], list) and settings["vnext"]:
            return int(settings["vnext"][0].get("port", 0))
        if "servers" in settings and isinstance(settings["servers"], list) and settings["servers"]:
            return int(settings["servers"][0].get("port", 0))
        if "port" in settings:
            try:
                return int(settings["port"])
            except (ValueError, TypeError):
                return 0
        return 0
