# Parser Interaction Matrix

This document defines the strict interaction permutations between Transport networks and Security protocols as enforced by the BaseParser layer.

## Security & Transport Permutations

| Security Type | Transport Network | Outcome | Notes |
|---------------|-------------------|---------|-------|
| REALITY       | `raw` (tcp)       | **VALID** | Standard XTLS-Reality transport |
| REALITY       | `grpc`            | **VALID** | |
| REALITY       | `xhttp`           | **VALID** | |
| REALITY       | `websocket` (`ws`)| **REJECT** | `ValidationError`: REALITY unsupported with network websocket |
| REALITY       | `mkcp` (`kcp`)    | **REJECT** | `ValidationError`: REALITY unsupported with network mkcp |
| REALITY       | `httpupgrade`     | **REJECT** | `ValidationError`: REALITY unsupported with network httpupgrade |
| REALITY       | `hysteria`        | **REJECT** | `ValidationError`: REALITY unsupported with network hysteria |
| TLS           | `hysteria`        | **VALID** | Native requirement for Hysteria |
| None          | `hysteria`        | **REJECT** | `ValidationError`: Hysteria requires TLS |
| TLS           | *Any*             | **VALID** | |
| None          | *Any* (except hys)| **VALID** | |

## Protocol & Credentials Permutations

| Protocol   | Field Requirement             | Outcome if Missing/Malformed |
|------------|-------------------------------|------------------------------|
| `vless`    | UUID (`user_id`)              | `ValidationError` (Missing or Invalid Format) |
| `vmess`    | UUID (`user_id`)              | `ValidationError` (Missing or Invalid Format) |
| `trojan`   | Password (`password`)         | `ValidationError` (Missing) |
| `shadowsocks` | Method & Password          | `ValidationError` (Missing) |

## Semantic Enforcements
These behaviors will be tested in the Protocol runners (`protocols/test_*.py`) iterating over pure data objects from the `matrix/` definitions.
