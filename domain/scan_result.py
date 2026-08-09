from dataclasses import dataclass, field
import time

@dataclass
class ScanResult:
    status: str = "Untested"
    latency_ms: float = -1.0
    outbound_ip: str = ""
    country: str = ""
    city: str = ""
    isp: str = ""
    error_message: str = ""
    scan_time: float = field(default_factory=time.time)
