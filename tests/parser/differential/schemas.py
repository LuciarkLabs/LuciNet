from typing import TypedDict, Literal, Union, Any, Optional
import re

class GoldenVector(TypedDict):
    id: str
    input: Any
    expected_kind: Literal["value", "error"]
    expected: Optional[Any]
    expected_error: Optional[str]
    source: str
    reference_commit: str

def validate_vectors(vectors: Any) -> list[GoldenVector]:
    if not isinstance(vectors, list):
        raise ValueError("Golden vector file must contain a top-level JSON array (list)")

    ALLOWED_KEYS = {
        "id",
        "input",
        "expected_kind",
        "expected",
        "expected_error",
        "source",
        "reference_commit",
    }

    for idx, v in enumerate(vectors):
        if not isinstance(v, dict):
            raise ValueError(f"Vector at index {idx} must be a JSON object (dict)")
            
        v_id = v.get("id", f"<unknown at index {idx}>")
        
        if not isinstance(v.get("id"), str) or not v["id"].strip():
            raise ValueError(f"Vector {v_id}: missing, empty, or invalid 'id' (must be non-empty str)")
            
        if "input" not in v:
            raise ValueError(f"Vector {v_id}: missing 'input'")
            
        expected_kind = v.get("expected_kind")
        if expected_kind not in ("value", "error"):
            raise ValueError(f"Vector {v_id}: 'expected_kind' must be strictly 'value' or 'error'")
            
        if not isinstance(v.get("source"), str) or not v["source"].strip():
            raise ValueError(f"Vector {v_id}: missing, empty, or invalid 'source' (must be non-empty str)")
            
        ref_commit = v.get("reference_commit")
        if not isinstance(ref_commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", ref_commit):
            raise ValueError(f"Vector {v_id}: 'reference_commit' must be exactly a 40-character hex SHA-1")

        extra_keys = set(v.keys()) - ALLOWED_KEYS
        if extra_keys:
            raise ValueError(f"Vector {v_id}: contains unauthorized extra keys: {extra_keys}")

        if expected_kind == "value":
            if "expected" not in v:
                raise ValueError(f"Vector {v_id}: missing 'expected' (required when expected_kind='value')")
            if "expected_error" in v:
                raise ValueError(f"Vector {v_id}: 'expected_error' is strictly forbidden when expected_kind='value'")
        elif expected_kind == "error":
            if "expected_error" not in v or not isinstance(v["expected_error"], str) or not v["expected_error"].strip():
                raise ValueError(f"Vector {v_id}: missing, empty, or invalid 'expected_error' (must be non-empty str when expected_kind='error')")
            if "expected" in v:
                raise ValueError(f"Vector {v_id}: 'expected' is strictly forbidden when expected_kind='error'")
    
    return vectors  # type: ignore

def load_vectors(json_path: str) -> list[GoldenVector]:
    import json
    with open(json_path, 'r', encoding='utf-8') as f:
        raw_vectors = json.load(f)
    return validate_vectors(raw_vectors)
