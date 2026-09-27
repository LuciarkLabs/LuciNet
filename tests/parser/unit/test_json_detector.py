from parser.json_detector import JsonDetector, JsonConfigType

def test_detect_full_config():
    payload = '{"inbounds": [{"protocol": "socks"}], "outbounds": [{"protocol": "vless"}]}'
    assert JsonDetector.detect(payload) == JsonConfigType.FULL_XRAY_CONFIG

def test_detect_single_outbound():
    payload = '{"protocol": "vless", "settings": {}}'
    assert JsonDetector.detect(payload) == JsonConfigType.SINGLE_OUTBOUND

def test_detect_outbound_array():
    payload = '[{"protocol": "vless", "settings": {}}, {"protocol": "vmess", "settings": {}}]'
    assert JsonDetector.detect(payload) == JsonConfigType.OUTBOUND_ARRAY

def test_detect_invalid_json():
    payload = "not json"
    assert JsonDetector.detect(payload) == JsonConfigType.INVALID_OR_NOT_XRAY

def test_detect_not_xray_dict():
    payload = '{"random": "key"}'
    assert JsonDetector.detect(payload) == JsonConfigType.INVALID_OR_NOT_XRAY

def test_detect_empty_array():
    payload = '[]'
    assert JsonDetector.detect(payload) == JsonConfigType.INVALID_OR_NOT_XRAY
