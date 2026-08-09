import json
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from utils.logger import get_logger
from utils.base64_helper import decode_base64

logger = get_logger("Normalizer")
IGNORED_PARAMS = {"remark", "name", "group", "host", "core"}

def normalize_config_url(raw_url: str) -> str:
    try:
        if raw_url.startswith("vmess://"):
            decoded = decode_base64(raw_url[8:])
            data = json.loads(decoded)
            for key in ["ps", "v", "host"]:
                data.pop(key, None)
            if "port" in data:
                data["port"] = int(data["port"])
            return json.dumps(data, sort_keys=True)
        else:
            parsed = urlparse(raw_url)
            query_params = parse_qsl(parsed.query, keep_blank_values=True)
            filtered_params = [
                (k.lower(), v)
                for k, v in query_params
                if k.lower() not in IGNORED_PARAMS
            ]
            sorted_query = urlencode(sorted(filtered_params))

            return urlunparse(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    parsed.path,
                    "",
                    sorted_query,
                    "",
                )
            )
    except Exception as e:
        logger.debug(f"Normalization failed: {e}")
        return raw_url.split("#")[0].lower()
