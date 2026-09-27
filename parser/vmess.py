import json
from domain.models import ProxyConfig
from parser.base import BaseParser
from parser.exceptions import ParseError, ValidationError
from parser.query import parse_uri_query
from parser.transport import populate_transport
from parser.security import populate_security
from parser.common import strict_unquote, parse_finalmask, process_unknown_params, set_lossless, get_host_port, safe_urlparse
from utils.base64_helper import decode_base64

class VMessParser(BaseParser):
    def parse(self, raw_url: str) -> ProxyConfig:
        if raw_url.lower().startswith("vmess://"):
            b64_part = raw_url[8:]
            if "?" in b64_part or "@" in b64_part:
                return self.parse_aead_uri(raw_url)
            else:
                return self.parse_legacy_json(raw_url, b64_part)
        else:
            raise ParseError("Not a vmess link")
            
    def parse_aead_uri(self, raw_url: str) -> ProxyConfig:
        parsed = safe_urlparse(raw_url)
        q = parse_uri_query(parsed.query)
        server, port = get_host_port(parsed)
            
        config = ProxyConfig(
            raw_url=raw_url,
            protocol="vmess",
            remark=strict_unquote(parsed.fragment),
            server=server,
            port=port
        )
        config.user_id = strict_unquote(parsed.username) if parsed.username else ""
        
        consumed = set()
        if "encryption" in q:
            enc = q["encryption"]
            if enc not in ("auto", "aes-128-gcm", "chacha20-poly1305", "none"):
                raise ValidationError(f"Invalid VMess encryption: {enc}")
            config.encryption = enc
            consumed.add("encryption")
        else: 
            config.encryption = "auto"
        
        consumed.update(populate_transport(config, q, default_net="tcp"))
        consumed.update(populate_security(config, q, config.server, default_sec="none"))
        
        if "fm" in q:
            parse_finalmask(q["fm"], config)
            consumed.add("fm")
        
        config.parse_meta.source_format = "vmess_aead_uri"
        process_unknown_params(q, consumed, config)
        
        self.validate(config)
        return config
        
    def parse_legacy_json(self, raw_url: str, b64_str: str) -> ProxyConfig:
        try:
            decoded = decode_base64(b64_str)
            data = json.loads(decoded)
            if not isinstance(data, dict):
                raise ParseError("VMess legacy JSON must be a dictionary")
        except Exception as e:
            raise ParseError(f"Invalid Base64 or JSON: {e}")
            
        try:
            p_val = int(data.get("port", 0))
        except (ValueError, TypeError):
            raise ValidationError("Malformed port")
            
        config = ProxyConfig(
            raw_url=raw_url,
            protocol="vmess",
            remark=str(data.get("ps", "")),
            server=str(data.get("add", "")),
            port=p_val
        )
        config.user_id = str(data.get("id", ""))
        
        legacy_mapped_keys = {"v", "ps", "add", "port", "id", "aid", "scy"}
        if "aid" in data: config.vmess_aid = str(data["aid"])
        if "scy" in data: 
            config.vmess_scy = str(data["scy"])
            if config.vmess_scy in ("auto", "aes-128-gcm", "chacha20-poly1305", "none", "zero"):
                config.encryption = config.vmess_scy
        
        q = {}
        if "net" in data: q["type"] = str(data["net"])
        if "tls" in data:
            tls_val = str(data["tls"])
            if tls_val in ("tls", "true", "1"): q["security"] = "tls"
            elif tls_val in ("none", "false", "0", ""): q["security"] = "none"
            else: q["security"] = tls_val
        if "sni" in data: q["sni"] = str(data["sni"])
        if "alpn" in data: q["alpn"] = str(data["alpn"])
        if "fp" in data: q["fp"] = str(data["fp"])
        if "host" in data: q["host"] = str(data["host"])
        if "path" in data: q["path"] = str(data["path"])
        
        if "allowInsecure" in data: q["allowInsecure"] = str(data["allowInsecure"])
        if "insecure" in data: q["insecure"] = str(data["insecure"])
        if "vcn" in data: q["vcn"] = str(data["vcn"])
        if "pcs" in data: q["pcs"] = str(data["pcs"])
        if "ech" in data: q["ech"] = str(data["ech"])
        
        consumed = set()
        consumed.update(populate_transport(config, q, default_net="tcp"))
        consumed.update(populate_security(config, q, config.server, default_sec="none"))
        
        config.parse_meta.source_format = "vmess_legacy_json"
        
        q_to_data_map = {
            "type": "net", "security": "tls", "sni": "sni", "alpn": "alpn", "fp": "fp", 
            "host": "host", "path": "path", "allowInsecure": "allowInsecure", 
            "insecure": "insecure", "vcn": "vcn", "pcs": "pcs", "ech": "ech"
        }
        for q_k in consumed:
            if q_k in q_to_data_map:
                legacy_mapped_keys.add(q_to_data_map[q_k])
        
        unknown_found = False
        for k, v in data.items():
            if k == "type" and str(v) != "none":
                config.parse_meta.extensions["legacy_type"] = str(v)
                config.parse_meta.warnings.append("Legacy VMess type preserved")
                unknown_found = True
            elif k not in legacy_mapped_keys and k != "type":
                config.parse_meta.extensions[f"legacy_unknown_{k}"] = str(v)
                unknown_found = True
        
        if unknown_found:
            set_lossless(config, False)
        else:
            set_lossless(config, True)
            
        self.validate(config)
        return config
