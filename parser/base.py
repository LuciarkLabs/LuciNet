from abc import ABC, abstractmethod
from domain.models import ProxyConfig
from parser.exceptions import ValidationError
from parser.common import parse_xray_uuid

class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw_url: str) -> ProxyConfig:
        pass
        
    def validate(self, config: ProxyConfig):
        if not config.server:
            raise ValidationError("Server/Host is required")
            
        if not config.port:
            raise ValidationError("Port is required")
            
        try:
            port = int(config.port)
            if not (1 <= port <= 65535):
                raise ValidationError("Port must be 1..65535")
            config.port = port
        except ValueError :
            raise ValidationError("Malformed port")
            
        sec = config.security_type
        net = config.transport.network
        
        if sec == "reality" and net not in ("raw", "xhttp", "grpc"):
            raise ValidationError(f"REALITY unsupported with network {net}")
            
        if net == "hysteria" and sec != "tls":
            raise ValidationError("Hysteria requires TLS")
            
        if config.protocol in ("vless", "vmess"):
            if not config.user_id:
                raise ValidationError(f"{config.protocol.upper()} requires UUID")
            try:
                val = parse_xray_uuid(config.user_id)
                config.user_id = val
            except ValueError as e:
                raise ValidationError(f"Invalid {config.protocol.upper()} UUID format: {e}")
                
        elif config.protocol == "trojan" and not config.password:
            raise ValidationError("Trojan requires password")
        elif config.protocol in ("ss", "shadowsocks"):
            if not config.method or not config.password:
                raise ValidationError("Shadowsocks requires method and password")
