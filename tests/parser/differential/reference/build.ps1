#!/usr/bin/env pwsh

$ErrorActionPreference = "Stop"

# Assuming go is extracted to l:\My projects\LuciNet\go
$env:PATH = "l:\My projects\LuciNet\go\bin;" + $env:PATH

cd "l:\My projects\LuciNet\tests\parser\differential\reference"
if (-not (Test-Path go.mod)) {
    go mod init ref_oracle
}
go get github.com/xtls/libxray@55cb29e214c5b77a1ba485da639a9e6b9b98adca
go build -o libxray_cli.exe main.go

echo "Build successful."
