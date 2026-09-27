from domain.models import ProxyConfig
from parser.base import BaseParser
from parser.exceptions import ParseError
from parser.query import parse_uri_query
from parser.transport import populate_transport
from parser.security import populate_security
from parser.common import strict_unquote, parse_finalmask, process_unknown_params, get_host_port, safe_urlparse

class TrojanParser(BaseParser):
    def parse(self, raw_url: str) -> ProxyConfig:
        parsed = safe_urlparse(raw_url)
        if parsed.scheme.lower() != "trojan":
            raise ParseError("Not a trojan link")
            
        q = parse_uri_query(parsed.query)
        server, port = get_host_port(parsed)
            
        config = ProxyConfig(
            raw_url=raw_url,
            protocol="trojan",
            remark=strict_unquote(parsed.fragment),
            server=server,
            port=port
        )
        config.password = strict_unquote(parsed.username) if parsed.username else ""
        
        consumed = set()
        consumed.update(populate_transport(config, q, default_net="tcp"))
        consumed.update(populate_security(config, q, config.server, default_sec="tls"))
        
        if "fm" in q:
            parse_finalmask(q["fm"], config)
            consumed.add("fm")
        
        config.parse_meta.source_format = "trojan_uri"
        process_unknown_params(q, consumed, config)
        
        self.validate(config)
        return config
