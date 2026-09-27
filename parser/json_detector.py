from enum import Enum
import json

class JsonConfigType(Enum):
    FULL_XRAY_CONFIG = "FULL_XRAY_CONFIG"
    SINGLE_OUTBOUND = "SINGLE_OUTBOUND"
    OUTBOUND_ARRAY = "OUTBOUND_ARRAY"
    INVALID_OR_NOT_XRAY = "INVALID_OR_NOT_XRAY"

class JsonDetector:
    @staticmethod
    def detect(payload: str) -> JsonConfigType:
        try:
            data = json.loads(payload)
        except Exception:
            return JsonConfigType.INVALID_OR_NOT_XRAY
            
        if isinstance(data, dict):
            inbounds = data.get("inbounds")
            outbounds = data.get("outbounds")
            
            if isinstance(inbounds, list) and isinstance(outbounds, list):
                return JsonConfigType.FULL_XRAY_CONFIG
                
            if "protocol" in data and "settings" in data:
                return JsonConfigType.SINGLE_OUTBOUND
                
        if isinstance(data, list) and len(data) > 0:
            if all(isinstance(item, dict) and "protocol" in item and "settings" in item for item in data):
                return JsonConfigType.OUTBOUND_ARRAY
                
        return JsonConfigType.INVALID_OR_NOT_XRAY
