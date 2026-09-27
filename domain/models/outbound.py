from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class MuxConfig:
    enabled: bool = False
    concurrency: int = 0
    xudp_concurrency: int = 0
    xudp_proxy_udp443: str = "reject"



@dataclass
class OutboundOptions:
    tag: str = ""
    send_through: str = ""
    target_strategy: str = "AsIs"
    mux: Optional[MuxConfig] = None



