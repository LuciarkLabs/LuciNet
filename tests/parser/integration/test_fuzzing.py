import pytest
import urllib.parse
import json
import base64
from hypothesis import given, settings, HealthCheck, strategies as st
from parser.factory import ParserFactory
from parser.exceptions import ParseError
from domain.models import ProxyConfig


@pytest.fixture(scope="module")
def parser_factory():
    return ParserFactory()

@settings(max_examples=1000, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    scheme=st.sampled_from(["vless", "vmess", "trojan", "ss", "shadowsocks", "hysteria2", "invalid_scheme"]),
    userinfo=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-!@#$%", min_size=0, max_size=50),
    host=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789.-", min_size=1, max_size=20),
    port=st.one_of(st.integers(min_value=-1000, max_value=100000), st.text(min_size=0, max_size=5)),
    query=st.dictionaries(st.text(min_size=1, max_size=10), st.text(min_size=0, max_size=20), max_size=10),
    fragment=st.text(min_size=0, max_size=20)
)
def test_fuzz_url_parsing(parser_factory, scheme, userinfo, host, port, query, fragment):
    netloc = host
    if port != "":
        netloc = f"{host}:{port}"
    if userinfo:
        netloc = f"{userinfo}@{netloc}"
        
    query_str = urllib.parse.urlencode(query)
    
    parts = (scheme, netloc, "", "", query_str, fragment)
    fuzz_url = urllib.parse.urlunparse(parts)
    
    try:
        result = parser_factory.parse_url(fuzz_url)
        assert isinstance(result, ProxyConfig), f"Parser returned unexpected type: {type(result).__name__}"
    except ParseError:
        pass
    except Exception as e:
        pytest.fail(f"CRITICAL: Parser crashed with unhandled exception: {type(e).__name__}: {e}\nInput: {fuzz_url}")

@settings(max_examples=1000, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(garbage=st.text(min_size=0, max_size=1000))
def test_fuzz_garbage_strings(parser_factory, garbage):
    try:
        result = parser_factory.parse_url(garbage)
        assert isinstance(result, ProxyConfig), f"Parser returned unexpected type: {type(result).__name__}"
    except ParseError:
        pass
    except Exception as e:
        pytest.fail(f"CRITICAL: Parser crashed with unhandled exception on garbage string: {type(e).__name__}: {e}\nInput: {garbage}")

@settings(max_examples=1000, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    scheme=st.sampled_from(["vmess", "ss"]),
    payload=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=", min_size=0, max_size=500)
)
def test_fuzz_legacy_b64_formats(parser_factory, scheme, payload):
    url = f"{scheme}://{payload}"
    try:
        result = parser_factory.parse_url(url)
        assert isinstance(result, ProxyConfig), f"Parser returned unexpected type: {type(result).__name__}"
    except ParseError:
        pass
    except Exception as e:
        pytest.fail(f"CRITICAL: Parser crashed with unhandled exception on b64 fuzzing: {type(e).__name__}: {e}\nInput: {url}")

@settings(max_examples=1000, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    scheme=st.sampled_from(["vmess", "ss"]),
    json_val=st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(),
        st.booleans(),
        st.none(),
        st.lists(st.text()),
        st.lists(st.integers())
    )
)
def test_fuzz_valid_json_invalid_types(parser_factory, scheme, json_val):
    json_str = json.dumps(json_val)
    b64_payload = base64.b64encode(json_str.encode('utf-8')).decode('ascii')
    
    url = f"{scheme}://{b64_payload}"
    try:
        result = parser_factory.parse_url(url)
        assert isinstance(result, ProxyConfig), f"Parser returned unexpected type: {type(result).__name__}"
    except ParseError:
        pass
    except Exception as e:
        pytest.fail(f"CRITICAL: Parser crashed on perfectly valid non-dict JSON ({json_str}): {type(e).__name__}: {e}\nInput: {url}")

