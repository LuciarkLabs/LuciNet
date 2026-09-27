# Differential Reference Oracle

This directory contains the integration boundary for executing true black-box differential tests against the upstream Go parser (`libXray` / `Xray-core`).

## Architecture

1. **`main.go`**: A thin Go wrapper CLI. It imports the exact pinned revision of `libXray` (e.g. `ConvertShareLinksToXrayJson`) and outputs normalized JSON (or errors).
2. **`runner.py`**: A Python wrapper that executes the Go CLI (via `subprocess`), passing the `vector.input` (raw URI) and capturing `stdout`/`stderr`.
3. **`canonicalize.py`**: A normalizer that maps the raw Go JSON struct field names (like `add`, `port`, `net`, `tls`) into the semantic Python schema (`ProxyConfig` dictionary representation) so they can be deeply compared.

## Provenance & Auditing

The vectors in `../vectors/` are hardcoded snapshots (Golden Vectors). Their provenance is defined by the `reference_commit` inside each vector. 

To prove that the Python implementation matches Go, the test `test_protocols_xray_differential.py` executes the oracle directly:

```
[Python Parser] -> Python ProxyConfig -> (dict)
                                          == (Compare)
[Go Oracle] -> Xray JSON -> canonicalize -> (dict)
```

## Setup

Since Python cannot natively execute Go code, you must compile the Go binary before running the differential test suite:

```bash
cd tests/parser/differential/reference
go mod init ref_oracle
go get github.com/xtls/libxray@55cb498e87853cb5fceae01c519d08eab917cc54
go build -o libxray_cli.exe main.go
```

If the binary `libxray_cli.exe` is missing from your PATH or environment, the differential tests will automatically `pytest.skip()`.
