import os
import re

p1 = 'l:/My projects/LuciNet/tests/parser/differential/reference/xray-core/transport/internet/tls/config.go'
with open(p1, 'r', encoding='utf-8') as f:
    c1 = f.read()
c1 = c1.replace('for suite := range strings.SplitSeq(c.CipherSuites, ":") {', 'for _, suite := range strings.Split(c.CipherSuites, ":") {')
with open(p1, 'w', encoding='utf-8') as f:
    f.write(c1)

p2 = 'l:/My projects/LuciNet/tests/parser/differential/reference/xray-core/transport/internet/finalmask/xmc/protocol.go'
with open(p2, 'r', encoding='utf-8') as f:
    c2 = f.read()
c2 = re.sub(r'new\(String\(reason\)\)', 'func() *String { s := String(reason); return &s }()', c2)
with open(p2, 'w', encoding='utf-8') as f:
    f.write(c2)

p3 = 'l:/My projects/LuciNet/tests/parser/differential/reference/xray-core/transport/internet/finalmask/xmc/server.go'
with open(p3, 'r', encoding='utf-8') as f:
    c3 = f.read()
c3 = re.sub(r'new\(String\(statusResponse\)\)', 'func() *String { s := String(statusResponse); return &s }()', c3)
with open(p3, 'w', encoding='utf-8') as f:
    f.write(c3)

p4 = 'l:/My projects/LuciNet/tests/parser/differential/reference/xray-core/transport/internet/tls/ech.go'
with open(p4, 'r', encoding='utf-8') as f:
    c4 = f.read()
c4 = c4.replace('IdleConnTimeout:       90 * time.Second,', '')
with open(p4, 'w', encoding='utf-8') as f:
    f.write(c4)
