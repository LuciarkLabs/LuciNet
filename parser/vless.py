from domain.models import ProxyConfig
from parser.base import BaseParser
from parser.exceptions import ParseError, ValidationError
from parser.query import parse_uri_query
from parser.transport import populate_transport
from parser.security import populate_security
from parser.common import parse_finalmask, process_unknown_params, get_host_port, safe_urlparse, strict_unquote

class VlessParser(BaseParser):
    def parse(self, raw_url: str) -> ProxyConfig:
        parsed = safe_urlparse(raw_url)
        if parsed.scheme.lower() != "vless":
            raise ParseError("Not a vless link")
            
        q = parse_uri_query(parsed.query)
        server, port = get_host_port(parsed)
            
        config = ProxyConfig(
            raw_url=raw_url,
            protocol="vless",
            remark=strict_unquote(parsed.fragment) if parsed.fragment else "",
            server=server,
            port=port
        )
        config.user_id = strict_unquote(parsed.username) if parsed.username else ""
        
        consumed = set()
        
        if "encryption" in q:
            enc = q["encryption"]
            enc_clean = enc.strip().lower()
            if enc_clean in ("", "none"):
                config.encryption = "none"
            else:
                parts = enc.split('.')
                if len(parts) < 4:
                    raise ValidationError(f"Invalid VLESS ML-KEM structure (missing blocks): {enc}")
                if parts[0] != "mlkem768x25519plus":
                    raise ValidationError(f"Invalid VLESS ML-KEM handshake: {parts[0]}")
                if parts[1] not in ("native", "xorpub", "random"):
                    raise ValidationError(f"Invalid VLESS ML-KEM appearance: {parts[1]}")
                
                session = parts[2]
                if session not in ("1rtt", "0rtt"):
                    raise ValidationError(f"Invalid VLESS ML-KEM session time: {session}")
                
                from parser.common import decode_raw_url_base64
                for r in parts[3:]:
                    if len(r) < 20:
                        continue
                    try:
                        b = decode_raw_url_base64(r)
                    except Exception as e:
                        raise ValidationError(f"Invalid VLESS ML-KEM padding Base64URL: {e}")
                    if len(b) != 32 and len(b) != 1184:
                        raise ValidationError(f"Invalid VLESS ML-KEM padding decoded length: {len(b)}")
                config.encryption = enc
            consumed.add("encryption")
        else:
            config.encryption = "none"
            
        if "flow" in q:
            flow = q["flow"]
            if flow not in ("", "xtls-rprx-vision", "xtls-rprx-vision-udp443"):
                raise ValidationError(f"Invalid VLESS flow: {flow}")
            config.flow = flow
            consumed.add("flow")
        
        consumed.update(populate_transport(config, q, default_net="tcp"))
        consumed.update(populate_security(config, q, config.server, default_sec="none"))
        
        if "fm" in q:
            parse_finalmask(q["fm"], config)
            consumed.add("fm")
        
        config.parse_meta.source_format = "vless_uri"
        process_unknown_params(q, consumed, config)
        
        self.validate(config)
        return config
