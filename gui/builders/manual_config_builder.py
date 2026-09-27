import urllib.parse
import base64
import json
from dataclasses import dataclass

@dataclass
class ManualConfigInput:
    protocol: str
    server: str
    port: int
    auth: str
    remark: str = ""

    network: str = "raw"
    security: str = "none"

    flow: str = ""
    encryption: str = "none"
    
    vmess_mode: str = "aead"
    vmess_encryption: str = "auto"
    vmess_legacy_scy: str = "auto"
    
    ss_method: str = "aes-128-gcm"
    ss_uot: bool = False
    ss_plugin: str = ""

    path: str = ""
    host: str = ""
    service_name: str = ""
    grpc_mode: str = ""
    grpc_authority: str = ""
    xhttp_mode: str = ""
    xhttp_extra: str = ""
    mkcp_mtu: str = ""
    mkcp_tti: str = ""
    
    sni: str = ""
    fp: str = ""
    alpn: str = ""
    ech: str = ""
    pcs: str = ""
    vcn: str = ""
    
    pbk: str = ""
    sid: str = ""
    spx: str = ""
    pqv: str = ""
    
    final_mask: str = ""
    allow_insecure: bool = False


class ManualConfigBuilder:
    @staticmethod
    def build(config: ManualConfigInput) -> str:
        protocol = config.protocol.lower()
        
        if config.security == "reality" and config.network not in ("raw", "xhttp", "grpc"):
            raise ValueError(f"Reality is not supported with network {config.network}")
        if config.network == "hysteria" and config.security != "tls":
            raise ValueError(f"Hysteria requires TLS security, got {config.security}")

        if protocol == "vless":
            return ManualConfigBuilder._build_vless(config)
        elif protocol == "vmess":
            if config.vmess_mode == "legacy":
                if config.security == "reality":
                    raise ValueError("Reality is not supported for VMess Legacy")
                if config.network not in ("raw", "websocket", "ws", "httpupgrade"):
                    raise ValueError(f"Transport {config.network} is not supported for VMess Legacy")
                return ManualConfigBuilder._build_vmess_legacy(config)
            else:
                return ManualConfigBuilder._build_vmess_aead(config)
        elif protocol == "trojan":
            return ManualConfigBuilder._build_trojan(config)
        elif protocol == "ss":
            return ManualConfigBuilder._build_ss(config)
        raise ValueError(f"Unsupported protocol: {protocol}")

    @staticmethod
    def _format_server(server: str) -> str:
        if ":" in server and not server.startswith("["):
            return f"[{server}]"
        return server

    @staticmethod
    def _encode_remark(remark: str) -> str:
        if not remark:
            return ""
        return "#" + urllib.parse.quote(remark, safe="")
        
    @staticmethod
    def _encode_userinfo(auth: str) -> str:
        return urllib.parse.quote(auth, safe="")
        
    @staticmethod
    def _encode_query_val(val: str) -> str:
        return urllib.parse.quote(val, safe="")

    @staticmethod
    def _build_query_params(config: ManualConfigInput, exclude_keys: list | None = None) -> str:
        protocol = config.protocol.lower()
        if exclude_keys is None:
            exclude_keys = []
            
        params = {}
        
        if config.network != "raw":
            params["type"] = config.network
            
        if config.security != "none" or protocol == "trojan":
            params["security"] = config.security

        if protocol == "vless":
            if config.encryption != "none":
                params["encryption"] = ManualConfigBuilder._encode_query_val(config.encryption)
            if config.flow:
                params["flow"] = config.flow
                
        if protocol == "vmess" and config.vmess_mode == "aead":
            if config.vmess_encryption:
                params["encryption"] = ManualConfigBuilder._encode_query_val(config.vmess_encryption)

        if config.security in ("tls", "reality"):
            if config.sni:
                params["sni"] = ManualConfigBuilder._encode_query_val(config.sni)
            if config.fp:
                params["fp"] = ManualConfigBuilder._encode_query_val(config.fp)
            if config.alpn:
                params["alpn"] = ManualConfigBuilder._encode_query_val(config.alpn)
            if config.ech:
                params["ech"] = ManualConfigBuilder._encode_query_val(config.ech)
            if config.pcs:
                params["pcs"] = ManualConfigBuilder._encode_query_val(config.pcs)
            if config.vcn:
                params["vcn"] = ManualConfigBuilder._encode_query_val(config.vcn)
            if config.allow_insecure:
                params["allowInsecure"] = "1"

        if config.security == "reality":
            if config.pbk:
                params["pbk"] = ManualConfigBuilder._encode_query_val(config.pbk)
            if config.sid:
                params["sid"] = ManualConfigBuilder._encode_query_val(config.sid)
            if config.spx:
                params["spx"] = ManualConfigBuilder._encode_query_val(config.spx)
            if config.pqv:
                params["pqv"] = ManualConfigBuilder._encode_query_val(config.pqv)

        if config.network in ("ws", "websocket"):
            if config.path:
                params["path"] = ManualConfigBuilder._encode_query_val(config.path)
            if config.host:
                params["host"] = ManualConfigBuilder._encode_query_val(config.host)
        elif config.network == "grpc":
            if config.service_name:
                params["serviceName"] = ManualConfigBuilder._encode_query_val(config.service_name)
            if config.grpc_mode:
                params["mode"] = ManualConfigBuilder._encode_query_val(config.grpc_mode)
            if config.grpc_authority:
                params["authority"] = ManualConfigBuilder._encode_query_val(config.grpc_authority)
        elif config.network == "xhttp":
            if config.path:
                params["path"] = ManualConfigBuilder._encode_query_val(config.path)
            if config.host:
                params["host"] = ManualConfigBuilder._encode_query_val(config.host)
            if config.xhttp_mode:
                params["mode"] = ManualConfigBuilder._encode_query_val(config.xhttp_mode)
            if config.xhttp_extra:
                params["extra"] = ManualConfigBuilder._encode_query_val(config.xhttp_extra)
        elif config.network == "mkcp":
            if config.mkcp_mtu:
                params["mtu"] = config.mkcp_mtu
            if config.mkcp_tti:
                params["tti"] = config.mkcp_tti
        elif config.network == "httpupgrade":
            if config.path:
                params["path"] = ManualConfigBuilder._encode_query_val(config.path)
            if config.host:
                params["host"] = ManualConfigBuilder._encode_query_val(config.host)
        
        if config.final_mask:
            params["fm"] = ManualConfigBuilder._encode_query_val(config.final_mask)
            
        for k in exclude_keys:
            params.pop(k, None)

        if not params:
            return ""
            
        return "?" + "&".join(f"{k}={v}" for k, v in params.items())

    @staticmethod
    def _build_vless(config: ManualConfigInput) -> str:
        server = ManualConfigBuilder._format_server(config.server)
        query = ManualConfigBuilder._build_query_params(config)
        remark = ManualConfigBuilder._encode_remark(config.remark)
        auth = ManualConfigBuilder._encode_userinfo(config.auth)
        return f"vless://{auth}@{server}:{config.port}{query}{remark}"

    @staticmethod
    def _build_vmess_aead(config: ManualConfigInput) -> str:
        server = ManualConfigBuilder._format_server(config.server)
        query = ManualConfigBuilder._build_query_params(config)
        remark = ManualConfigBuilder._encode_remark(config.remark)
        auth = ManualConfigBuilder._encode_userinfo(config.auth)
        return f"vmess://{auth}@{server}:{config.port}{query}{remark}"

    @staticmethod
    def _build_trojan(config: ManualConfigInput) -> str:
        server = ManualConfigBuilder._format_server(config.server)
        query = ManualConfigBuilder._build_query_params(config)
        remark = ManualConfigBuilder._encode_remark(config.remark)
        auth = ManualConfigBuilder._encode_userinfo(config.auth)
        return f"trojan://{auth}@{server}:{config.port}{query}{remark}"

    @staticmethod
    def _build_vmess_legacy(config: ManualConfigInput) -> str:
        data = {
            "v": "2",
            "ps": config.remark,
            "add": config.server,
            "port": str(config.port),
            "id": config.auth,
            "aid": "0",
            "scy": config.vmess_legacy_scy,
            "net": config.network if config.network != "raw" else "tcp",
            "type": "none"
        }
        
        if config.security == "tls":
            data["tls"] = "tls"
            if config.sni: data["sni"] = config.sni
            if config.alpn: data["alpn"] = config.alpn
            if config.fp: data["fp"] = config.fp
            if config.allow_insecure: data["allowInsecure"] = "true"
            
        if config.network in ("ws", "websocket"):
            if config.path: data["path"] = config.path
            if config.host: data["host"] = config.host
        elif config.network == "httpupgrade":
            if config.path: data["path"] = config.path
            if config.host: data["host"] = config.host
            
        json_str = json.dumps(data, separators=(",", ":"))
        b64_str = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        return f"vmess://{b64_str}"

    @staticmethod
    def _build_ss(config: ManualConfigInput) -> str:
        server = ManualConfigBuilder._format_server(config.server)
        remark = ManualConfigBuilder._encode_remark(config.remark)
        
        auth_str = f"{config.ss_method}:{config.auth}"
        auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        
        url = f"ss://{auth_b64}@{server}:{config.port}"
        
        params = []
        if config.ss_plugin:
            params.append(f"plugin={ManualConfigBuilder._encode_query_val(config.ss_plugin)}")
        if config.ss_uot:
            params.append("uot=1")
            
        if params:
            url += "?" + "&".join(params)
            
        url += remark
        return url
