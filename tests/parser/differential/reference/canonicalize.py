from typing import Dict, Any

def canonicalize_go_xray_json(go_json: Dict[str, Any]) -> Dict[str, Any]:
    if "outbounds" not in go_json or not isinstance(go_json["outbounds"], list) or len(go_json["outbounds"]) == 0:
        raise ValueError("Failed to extract required field: missing or empty 'outbounds' array")
    
    outbound = go_json["outbounds"][0]
    
    if "protocol" not in outbound:
        raise ValueError("Failed to extract required field: 'protocol'")
    
    protocol = outbound["protocol"]
    settings = outbound.get("settings", {})
    stream = outbound.get("streamSettings", {})
    
    out = {
        "protocol": protocol,
        "remark": outbound.get("tag", "")
    }
    
    if "address" not in settings:
        raise ValueError("Failed to extract required field: 'address'")
    if "port" not in settings:
        raise ValueError("Failed to extract required field: 'port'")
        
    out["server"] = settings["address"]
    out["port"] = settings["port"]
    
    if protocol == "vless" or protocol == "vmess":
        if "id" not in settings:
            raise ValueError(f"Failed to extract required field: 'id' for {protocol}")
        out["user_id"] = settings["id"]
    elif protocol == "trojan" or protocol == "shadowsocks":
        if "password" not in settings:
            raise ValueError(f"Failed to extract required field: 'password' for {protocol}")
        out["password"] = settings["password"]
        
        if protocol == "shadowsocks":
            if "method" not in settings:
                raise ValueError("Failed to extract required field: 'method'")
            out["method"] = settings["method"]
            
    out["network"] = stream.get("network", "raw")
    if out["network"] == "tcp": out["network"] = "raw"
    if out["network"] == "ws": out["network"] = "websocket"
    
    security = stream.get("security", "none")
    out["security_type"] = security
    
    if security == "tls":
        tls_settings = stream.get("tlsSettings", {})
        if "serverName" in tls_settings:
            out["sni"] = tls_settings["serverName"]
        if "fingerprint" in tls_settings:
            out["fp"] = tls_settings["fingerprint"]
    elif security == "reality":
        reality_settings = stream.get("realitySettings", {})
        if "serverName" in reality_settings:
            out["sni"] = reality_settings["serverName"]
        if "fingerprint" in reality_settings:
            out["fp"] = reality_settings["fingerprint"]
        if "password" in reality_settings:
            out["pbk"] = reality_settings["password"]
            
    if out["network"] == "grpc":
        grpc_settings = stream.get("grpcSettings", {})
        if "serviceName" in grpc_settings:
            out["grpc_service_name"] = grpc_settings["serviceName"]
    elif out["network"] == "ws":
        ws_settings = stream.get("wsSettings", {})
        if "path" in ws_settings:
            out["path"] = ws_settings["path"]
            
    return out
