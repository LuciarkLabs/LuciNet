import re
import hashlib
import uuid
import base64

def strict_unquote(v: str) -> str:
    from urllib.parse import unquote
    if re.search(r'%(?![0-9a-fA-F]{2})', v):
        from parser.exceptions import ParseError
        raise ParseError(f"Malformed percent-encoding in: {v}")
    return unquote(v)

def parse_xray_uuid(s: str) -> str:
    b = s.encode('utf-8')
    if 1 <= len(b) <= 30:
        h = hashlib.sha1()
        h.update(b'\x00' * 16)
        h.update(b)
        u = bytearray(h.digest()[:16])
        u[6] = (u[6] & 0x0f) | (5 << 4)
        u[8] = (u[8] & 0x3f) | 0x80
        return str(uuid.UUID(bytes=bytes(u)))
    
    text = s
    u_bytes = bytearray(16)
    idx = 0
    text_len = len(text)
    
    for i in range(16):
        if idx < text_len and text[idx] == '-':
            idx += 1
        
        if idx + 2 > text_len:
            raise ValueError("Invalid UUID format (too short)")
            
        hex_pair = text[idx:idx+2]
        try:
            u_bytes[i] = int(hex_pair, 16)
        except ValueError:
            raise ValueError(f"Invalid UUID hex character: {hex_pair}")
            
        idx += 2
        
    if idx < text_len:
        raise ValueError("Invalid UUID format (extra characters)")
        
    return str(uuid.UUID(bytes=bytes(u_bytes)))

def decode_raw_url_base64(s: str) -> bytes:
    if len(s) % 4 == 1:
        raise ValueError("Invalid Base64RawURL length")
    if not re.fullmatch(r'[A-Za-z0-9_-]*', s):
        raise ValueError("Invalid Base64RawURL characters")
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))

def parse_finalmask(fm_raw: str, config):
    if fm_raw == "": return
    config.finalmask_raw = fm_raw
    try:
        import json
        parsed = json.loads(fm_raw)
        if isinstance(parsed, dict):
            config.finalmask = parsed
        else:
            raise ValueError()
    except Exception:
        config.finalmask = None
        config.parse_meta.warnings.append("FinalMask is not a valid JSON dict")
        set_lossless(config, False)

def set_lossless(config, val: bool):
    if config.parse_meta.lossless is False: return
    config.parse_meta.lossless = val

def process_unknown_params(q: dict, consumed_keys: set, config):
    unknown_found = False
    for k, v in q.items():
        if k not in consumed_keys:
            config.parse_meta.unknown_params[k] = str(v)
            unknown_found = True
    if unknown_found:
        set_lossless(config, False)
    elif config.parse_meta.lossless is None:
        set_lossless(config, True)

def get_host_port(parsed):
    from parser.exceptions import ValidationError
    try:
        port = parsed.port
    except ValueError:
        raise ValidationError("Malformed port")
    return parsed.hostname or "", port

def safe_urlparse(url: str):
    from urllib.parse import urlparse
    from parser.exceptions import ParseError
    try:
        return urlparse(url)
    except ValueError as e:
        raise ParseError(f"URL parsing failed: {e}")
