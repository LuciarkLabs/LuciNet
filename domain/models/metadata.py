import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class ParseMetadata:
    source_format: str = (
        ""
    )
    unknown_params: Dict[str, str] = field(default_factory=dict)
    extensions: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    lossless: Optional[bool] = None



@dataclass
class ProxyRuntime:
    country: str = ""
    city: str = ""
    isp: str = ""
    real_ip: str = ""
    ping: Optional[float] = None
    download_speed: Optional[float] = None
    status: str = "Untested"



@dataclass
class ProxyStorage:
    id: Optional[int] = None
    sub_id: Optional[int] = None
    group_name: str = "Default"
    first_seen: float = field(default_factory=time.time)
    last_scan: float = 0.0
    last_seen_alive: float = 0.0
    scan_count: int = 0



