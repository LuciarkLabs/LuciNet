from domain.models import ProxyConfig
from parser.exceptions import ValidationError

VALID_NETWORKS = {"raw", "xhttp", "mkcp", "grpc", "websocket", "httpupgrade", "hysteria"}

def populate_transport(config: ProxyConfig, q: dict[str, str], default_net: str = "tcp") -> set:
    consumed = set()
    if "type" not in q:
        network = default_net
    else:
        consumed.add("type")
        network = q["type"]
        if not network:
            raise ValidationError("Network (type) cannot be empty if explicitly provided")

    if network == "tcp": network = "raw"
    elif network == "ws": network = "websocket"
    elif network == "kcp": network = "mkcp"
    elif network == "splithttp": network = "xhttp"
    
    if network not in VALID_NETWORKS:
        raise ValidationError(f"Unsupported, legacy, or invalid-case network: {network}")
        
    config.transport.network = network
    
    if network in ("websocket", "httpupgrade", "xhttp"):
        if "path" in q:
            consumed.add("path")
            p = q["path"]
            if p == "": raise ValidationError("Explicit empty path is invalid")
            config.transport.path = p
        else:
            config.transport.path = "/"
            
        if "host" in q:
            consumed.add("host")
            config.transport.host = q["host"]
        
        if network == "xhttp":
            if "mode" in q:
                consumed.add("mode")
                config.transport.xhttp_mode = q["mode"]
            if "extra" in q:
                consumed.add("extra")
                config.transport.xhttp_extra = q["extra"]
                
    elif network == "grpc":
        if "serviceName" in q:
            consumed.add("serviceName")
            svc = q["serviceName"]
            if svc == "": raise ValidationError("gRPC serviceName cannot be explicit empty")
            config.transport.grpc_service_name = svc
            
        if "mode" in q:
            consumed.add("mode")
            mode = q["mode"]
            if mode == "": raise ValidationError("gRPC mode cannot be explicit empty")
            if mode not in ("gun", "multi", "guna"):
                raise ValidationError(f"Invalid gRPC mode {mode}")
            config.transport.grpc_mode = mode
        else:
            config.transport.grpc_mode = "gun"
            
        if "authority" in q:
            consumed.add("authority")
            config.transport.grpc_authority = q["authority"]
            
    elif network == "mkcp":
        if "mtu" in q:
            consumed.add("mtu")
            try: config.transport.kcp_mtu = int(q["mtu"])
            except Exception: raise ValidationError("invalid mkcp mtu")
        if "tti" in q:
            consumed.add("tti")
            try: config.transport.kcp_tti = int(q["tti"])
            except Exception: raise ValidationError("invalid mkcp tti")
            
    return consumed
