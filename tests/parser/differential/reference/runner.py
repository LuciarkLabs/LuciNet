import subprocess
import json
import os
import pytest
from typing import Dict, Any, Tuple, Optional

def run_go_reference(url: str) -> Tuple[bool, Any]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    go_bin = os.path.join(script_dir, "libxray_cli.exe")
    
    if not os.path.exists(go_bin):
        pytest.skip(f"Reference executable '{go_bin}' not found. Cannot run TRUE differential test.")
        
    try:
        result = subprocess.run([go_bin, url], capture_output=True, text=True, timeout=10)
        
        lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        json_line = ""
        for line in reversed(lines):
            if line.startswith('{') and line.endswith('}'):
                json_line = line
                break
                
        if not json_line:
            pytest.fail(f"Reference binary returned invalid JSON: {result.stdout.strip()}\nStderr: {result.stderr.strip()}")
            
        try:
            out = json.loads(json_line)
        except json.JSONDecodeError:
            pytest.fail(f"Reference binary returned invalid JSON: {result.stdout.strip()}\nStderr: {result.stderr.strip()}")
            
        if "ok" not in out:
            pytest.fail(f"Reference binary output missing 'ok' field: {out}")
            
        if out["ok"]:
            if "result" not in out:
                pytest.fail(f"Reference binary output missing 'result' field on success: {out}")
            return True, out["result"]
        else:
            if "error_kind" not in out:
                pytest.fail(f"Reference binary output missing 'error_kind' field on failure: {out}")
            return False, out["error_kind"]
            
    except subprocess.TimeoutExpired:
        pytest.fail("Reference Go binary timed out.")
    except Exception as e:
        pytest.fail(f"Failed to execute reference Go binary: {e}")
