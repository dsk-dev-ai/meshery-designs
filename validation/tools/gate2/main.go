package main

import (
	"fmt"
	"os"

	"github.com/meshery/meshkit/encoding"
	"github.com/meshery/schemas/models/v1beta3/design"
)

func main() {
	in, out := os.Args[1], os.Args[2]
	data, err := os.ReadFile(in)
	if err != nil {
		fmt.Fprintln(os.Stderr, "read:", err)
		os.Exit(1)
	}
	pf := &design.PatternFile{}
	if err := encoding.Unmarshal(data, pf); err != nil {
		fmt.Fprintln(os.Stderr, "UNMARSHAL FAILED:", err)
		os.Exit(2)
	}
	b, err := encoding.Marshal(pf)
	if err != nil {
		fmt.Fprintln(os.Stderr, "MARSHAL FAILED:", err)
		os.Exit(3)
	}
	if err := os.WriteFile(out, b, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "write:", err)
		os.Exit(4)
	}
	fmt.Printf("unmarshal OK\n")
	fmt.Printf("components    %d\n", len(pf.Components))
	fmt.Printf("relationships %d\n", len(pf.Relationships))
}
