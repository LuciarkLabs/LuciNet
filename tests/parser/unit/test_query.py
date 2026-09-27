import pytest
from parser.query import parse_uri_query
from parser.exceptions import ParseError

def test_query_normal():
    q = parse_uri_query("a=1&b=2")
    assert q == {"a": "1", "b": "2"}

def test_query_empty_string():
    q = parse_uri_query("")
    assert q == {}

def test_query_empty_component():
    with pytest.raises(ParseError, match="Empty query component"):
        parse_uri_query("a=1&&b=2")
    with pytest.raises(ParseError, match="Empty query component"):
        parse_uri_query("a=1&")

def test_query_duplicate_keys():
    with pytest.raises(ParseError, match="Duplicate parameter"):
        parse_uri_query("a=1&a=2")

def test_query_malformed_equals():
    with pytest.raises(ParseError, match="missing ="):
        parse_uri_query("a=1&b")

def test_query_strict_unquote():
    q = parse_uri_query("a=%20&b=%2F")
    assert q == {"a": " ", "b": "/"}
    with pytest.raises(ParseError):
        parse_uri_query("a=%ZZ")

def test_query_empty_key():
    with pytest.raises(ParseError, match="empty key"):
        parse_uri_query("=foo")

def test_query_multiple_equals():
    q = parse_uri_query("a=b=c&d=e=f=g")
    assert q == {"a": "b=c", "d": "e=f=g"}
