import pytest
import subprocess
import os
import json

def test_oracle_preflight():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    go_bin = os.path.join(script_dir, "reference", "libxray_cli.exe")
    
    if not os.path.exists(go_bin):
        pytest.skip(f"Reference executable '{go_bin}' not found. Cannot run TRUE differential test.")
        
    result = subprocess.run([go_bin, "invalid://url"], capture_output=True, text=True)
    try:
        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        json_line = next((l for l in reversed(lines) if l.startswith("{") and l.endswith("}")), "")
        out = json.loads(json_line)
    except json.JSONDecodeError:
        pytest.fail(f"Oracle did not return JSON. Stdout: {result.stdout}")
        
    assert "ok" in out, "CLI schema must include 'ok' field"
    assert out["ok"] is False
    assert "error_kind" in out
    
    result2 = subprocess.run([go_bin, "vless://feb54431-301b-52bb-a6dd-e1e93e81bb9e@127.0.0.1:443?type=tcp&security=none"], capture_output=True, text=True)
    lines2 = [l.strip() for l in result2.stdout.strip().split("\n") if l.strip()]
    json_line2 = next((l for l in reversed(lines2) if l.startswith("{") and l.endswith("}")), "")
    out2 = json.loads(json_line2)
    assert out2["ok"] is True
    assert "result" in out2
    assert isinstance(out2["result"], dict)
    
    libxray_dir = os.path.join(script_dir, "reference", "libxray")
    if os.path.exists(libxray_dir):
        rev = subprocess.run(["git", "-C", libxray_dir, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        assert rev == "55cb29e214c5b77a1ba485da639a9e6b9b98adca", f"libxray checkout is {rev}, expected 55cb29e214c5b77a1ba485da639a9e6b9b98adca"
        
        gomod_path = os.path.join(libxray_dir, "go.mod")
        with open(gomod_path, "r") as f:
            content = f.read()
            assert "github.com/xtls/xray-core v1.260327.1-0.20260908222543-52a412d9e2f5" in content, "libxray/go.mod does not specify the exact pinned xray-core version!"
