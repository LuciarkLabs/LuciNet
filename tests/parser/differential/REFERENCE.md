# Xray-Core & libXray Pinned References

This document records the exact snapshot of Xray-Core and libXray used to generate the Golden Vectors for the differential testing suite.

## 1. Xray-Core Reference (Primitives & Runtime Semantics)
- **Retrieval Date:** 2026-09-23
- **Repository URL:** https://github.com/XTLS/Xray-core
- **Commit SHA:** `d562d8947d3175db86b4fa849742433a9876cb63`
- **Source File Paths:**
  - `infra/conf/vless.go` (VLESS account.Encryption parsing, Flow validation)
  - `common/uuid/uuid.go` (UUID `ParseString` and `ParseBytes` logic)
  - `encoding/base64` (Go stdlib RawURLEncoding semantics used across Xray-Core)
- **Scope:** UUID mapping, Base64 padding/alphabet strictness, and primitive validation rules.

## 2. libXray Reference (Share-Link Behavior)
- **Retrieval Date:** 2026-09-23
- **Repository URL:** https://github.com/XTLS/libXray
- **Commit SHA:** `55cb29e214c5b77a1ba485da639a9e6b9b98adca`
- **Source File Paths:**
  - `share/parse_share.go` (Implementation of core parsing functions like `ParseShare` and protocol-specific parsers)
  - `share/convert_share.go` (`parseShareCandidates`)
- **Scope:** Protocol-level share link URI parsing for VLESS, VMess AEAD, Trojan, and Shadowsocks.
- **Exclusion:** Legacy VMess (JSON/Base64) is intentionally excluded from `libXray` differential testing and is handled separately in integration regression.
