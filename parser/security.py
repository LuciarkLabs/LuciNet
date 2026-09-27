from domain.models import ProxyConfig
from parser.exceptions import ValidationError
from parser.common import set_lossless

VALID_SECURITY = {"none", "tls", "reality"}

def populate_security(config: ProxyConfig, q: dict[str, str], remote_host: str, default_sec: str = "none") -> set:
    consumed = set()
    if "security" not in q:
        sec = default_sec
    else:
        consumed.add("security")
        sec = q["security"]
        if sec == "":
            raise ValidationError("Explicit empty security is invalid")
            
    if sec not in VALID_SECURITY:
        raise ValidationError(f"Invalid or invalid-case security type {sec}")
        
    config.security_type = sec
    
    if sec in ("tls", "reality"):
        if "sni" in q:
            consumed.add("sni")
            sni = q["sni"]
            if sni == "": raise ValidationError("Explicit empty SNI is invalid")
            config.tls.server_name = sni
        else:
            config.tls.server_name = remote_host
        
        if "fp" in q:
            consumed.add("fp")
            fp = q["fp"]
            if fp == "": raise ValidationError("Explicit empty fp is invalid")
            config.tls.fingerprint = fp
        else:
            config.tls.fingerprint = "chrome"

            
        if "alpn" in q:
            consumed.add("alpn")
            alpn_raw = q["alpn"]
            if alpn_raw == "": raise ValidationError("Explicit empty ALPN is invalid")
            alpns = alpn_raw.split(",")
            for a in alpns:
                if not a or any(ch.isspace() for ch in a):
                    raise ValidationError("Invalid ALPN format")
            config.tls.alpn = alpns
            
        if "ech" in q:
            consumed.add("ech")
            config.tls.ech_config_list = q["ech"]
        if "pcs" in q:
            consumed.add("pcs")
            config.tls.pinned_peer_cert_sha256 = q["pcs"]
        if "vcn" in q:
            consumed.add("vcn")
            config.tls.verify_peer_cert_by_name = q["vcn"]
        
    if sec == "reality":
        if "pbk" not in q:
            raise ValidationError("REALITY requires pbk")
        consumed.add("pbk")
        config.reality.password = q["pbk"]
        if "sid" in q:
            consumed.add("sid")
            config.reality.short_id = q["sid"]
        if "spx" in q:
            consumed.add("spx")
            config.reality.spider_x = q["spx"]
        if "pqv" in q:
            consumed.add("pqv")
            config.reality.mldsa65_verify = q["pqv"]
            
    for k in ("allowInsecure", "insecure"):
        if k in q:
            consumed.add(k)
            val = q[k]
            if val in ("1", "true"): config.tls.allow_insecure = True
            config.parse_meta.warnings.append(f"{k} is deprecated")
            set_lossless(config, False)
        
    return consumed
