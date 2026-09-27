import pytest
import os
from parser.common import decode_raw_url_base64
from tests.parser.differential.schemas import load_vectors

VECTOR_FILE = os.path.join(os.path.dirname(__file__), 'vectors/base64.json')
VECTORS = load_vectors(VECTOR_FILE)

EXPECTED_ERRORS = {
    "ValueError": ValueError,
}

@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["id"])
def test_decode_raw_url_base64_vectors(vector):
    if vector["expected_kind"] == "value":
        result = decode_raw_url_base64(vector["input"])
        assert result.hex() == vector["expected"]
    else:
        err_type = EXPECTED_ERRORS[vector["expected_error"]]
        with pytest.raises(err_type):
            decode_raw_url_base64(vector["input"])
