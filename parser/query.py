from parser.common import strict_unquote
from parser.exceptions import ParseError

def parse_uri_query(raw_query: str) -> dict[str, str]:
    result: dict[str, str] = {}
    if not raw_query: return result
    for part in raw_query.split("&"):
        if not part:
            raise ParseError("Empty query component is invalid")
        if "=" not in part:
            raise ParseError(f"Malformed query parameter (missing =): {part}")
        k, _, v = part.partition("=")
        if not k:
            raise ParseError("Malformed query parameter (empty key)")
        if k in result:
            raise ParseError(f"Duplicate parameter found: {k}")
        result[k] = strict_unquote(v)
    return result
