from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class TransportConfig:
    network: str = (
        "raw"
    )

    path: str = ""
    host: str = ""

    raw_header: Optional[Dict[str, Any]] = None

    grpc_service_name: str = ""
    grpc_authority: str = ""
    grpc_mode: str = "gun"
    grpc_user_agent: str = ""
    grpc_idle_timeout: Optional[int] = None
    grpc_health_check_timeout: Optional[int] = None
    grpc_permit_without_stream: Optional[bool] = None
    grpc_initial_windows_size: Optional[int] = None

    kcp_mtu: Optional[int] = None
    kcp_tti: Optional[int] = None
    kcp_uplink_capacity: Optional[int] = None
    kcp_downlink_capacity: Optional[int] = None
    kcp_cwnd_multiplier: Optional[int] = None
    kcp_max_sending_window: Optional[int] = None

    ws_headers: Dict[str, str] = field(default_factory=dict)
    ws_heartbeat_period: int = 0

    httpupgrade_headers: Dict[str, str] = field(default_factory=dict)

    xhttp_mode: str = ""
    xhttp_extra: str = ""

    hysteria: Optional[Dict[str, Any]] = None



