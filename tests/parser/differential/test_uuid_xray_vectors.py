import pytest
import os
from parser.common import parse_xray_uuid
from tests.parser.differential.schemas import load_vectors

VECTOR_FILE = os.path.join(os.path.dirname(__file__), 'vectors/uuid.json')
VECTORS = load_vectors(VECTOR_FILE)

EXPECTED_ERRORS = {
    "ValueError": ValueError,
}

@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["id"])
def test_parse_xray_uuid_vectors(vector):
    if vector["expected_kind"] == "value":
        result = parse_xray_uuid(vector["input"])
        assert result == vector["expected"]
    else:
        err_type = EXPECTED_ERRORS[vector["expected_error"]]
        with pytest.raises(err_type):
            parse_xray_uuid(vector["input"])
