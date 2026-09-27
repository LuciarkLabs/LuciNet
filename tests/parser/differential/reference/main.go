package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/xtls/libxray/share"
)

type Output struct {
	Ok        bool            `json:"ok"`
	ErrorKind string          `json:"error_kind,omitempty"`
	ErrorCode string          `json:"error_code,omitempty"`
	Result    json.RawMessage `json:"result,omitempty"`
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: libxray_cli <url>\n")
		os.Exit(1)
	}

	url := os.Args[1]

	// ConvertShareLinksToXrayJson string signature
	resStr, err := share.ConvertShareLinksToXrayJson(url, "")
	if err != nil {
		out := Output{
			Ok:        false,
			ErrorKind: "parse",
			ErrorCode: err.Error(),
		}
		b, _ := json.Marshal(out)
		fmt.Println(string(b))
		os.Exit(0)
	}

	out := Output{
		Ok:     true,
		Result: json.RawMessage(resStr),
	}
	b, _ := json.Marshal(out)
	fmt.Println(string(b))
}
