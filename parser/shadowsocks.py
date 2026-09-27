from domain.models import ProxyConfig
from parser.base import BaseParser
from parser.exceptions import ParseError, ValidationError
from parser.query import parse_uri_query
from utils.base64_helper import decode_base64
from parser.common import strict_unquote, process_unknown_params, safe_urlparse

class ShadowsocksParser(BaseParser):
    def parse(self, raw_url: str) -> ProxyConfig:
        parsed = safe_urlparse(raw_url)
        protocol = parsed.scheme.lower()
        if protocol not in ("ss", "shadowsocks"):
            raise ParseError("Not a shadowsocks link")
            
        q = parse_uri_query(parsed.query)
        remark = strict_unquote(parsed.fragment)
        
        try:
            core_part = raw_url.split("://", 1)[1].split("#")[0].split("?")[0]
        except IndexError:
            raise ParseError("Invalid link structure")
            
        core_part = strict_unquote(core_part).rstrip("/")
        
        is_legacy_base64 = False
        is_base64_userinfo = False
        
        if "@" not in core_part:
            try:
                decoded = decode_base64(core_part)
                if "@" in decoded:
                    core_part = decoded
                    is_legacy_base64 = True
            except Exception:
                pass
                
        if "@" not in core_part:
            raise ParseError("Invalid format, @ not found")
            
        auth_part, server_part = core_part.rsplit("@", 1)
        server_part = server_part.rstrip("/")
        
        if ":" not in auth_part:
            try:
                decoded_auth = decode_base64(auth_part)
                auth_part = decoded_auth
                is_base64_userinfo = True
            except Exception:
                pass
                
        if ":" in auth_part:
            method, password = auth_part.split(":", 1)
        else:
            method = auth_part
            password = ""
            
        if not is_base64_userinfo and not is_legacy_base64:
            method = strict_unquote(method)
            password = strict_unquote(password)
            
        server = ""
        port = None
        
        if "]" in server_part:
            if server_part.startswith("["):
                host_end = server_part.find("]")
                server = server_part[1:host_end]
                port_str = server_part[host_end + 1:]
                if port_str.startswith(":"):
                    port = port_str[1:]
            else:
                raise ValidationError("Malformed IPv6")
        else:
            if server_part.count(":") > 1:
                raise ValidationError("Unbracketed IPv6 is invalid")
            if ":" in server_part:
                server, port = server_part.rsplit(":", 1)
            else:
                server = server_part
                
        try:
            p_val = int(port) if port else 0
        except ValueError:
            raise ValidationError("Malformed port")
            
        config = ProxyConfig(
            raw_url=raw_url,
            protocol="shadowsocks",
            remark=remark,
            server=server,
            port=p_val
        )
        config.method = method
        config.password = password
        config.transport.network = "raw"
        config.security_type = "none"
        
        consumed = set()
        if "uot" in q:
            uot_val = q["uot"]
            if uot_val in ("1", "true"): config.ss_uot = True
            elif uot_val in ("0", "false"): config.ss_uot = False
            else: raise ValidationError("Invalid uot value")
            consumed.add("uot")
            
        plugin = q.get("plugin", "")
        if plugin:
            config.parse_meta.extensions["ss_plugin"] = plugin
            consumed.add("plugin")
            
        if is_legacy_base64: config.parse_meta.source_format = "shadowsocks_legacy_base64"
        elif is_base64_userinfo: config.parse_meta.source_format = "shadowsocks_base64_userinfo"
        else: config.parse_meta.source_format = "shadowsocks_sip002"
        
        process_unknown_params(q, consumed, config)
        
        self.validate(config)
        return config
