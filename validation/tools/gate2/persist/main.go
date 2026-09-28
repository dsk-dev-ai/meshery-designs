package main

// Simulates the Meshery production design-persist path traced at
// meshery/server/handlers/meshery_pattern_handler.go:374-376:
//
//	meshkitPatternHelpers.DehydratePattern(&requestPayload.DesignFile)
//	designFileBytes, err := encoding.Marshal(requestPayload.DesignFile)
//	provider.SaveMesheryPattern(..., PatternFile: string(designFileBytes))
//
// This writes what the server would actually persist, so the G2-E1/G2-E2
// classifications can be checked against the real stored document rather
// than against the intermediate struct.

import (
	"fmt"
	"os"

	"github.com/meshery/meshkit/encoding"
	"github.com/meshery/meshkit/models/patterns"
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

	// identity/topology census before dehydration
	compIDs, relIDs, selIDs, patches, ann := 0, 0, 0, 0, 0
	for _, c := range pf.Components {
		compIDs++
		if c != nil && c.Metadata.IsAnnotation {
			ann++
		}
	}
	for _, r := range pf.Relationships {
		relIDs++
		if r == nil || r.Selectors == nil {
			continue
		}
		for _, s := range *r.Selectors {
			selIDs += len(s.Allow.From) + len(s.Allow.To)
			for _, e := range s.Allow.From {
				if e.RelationshipDefinitionSelectorsPatch != nil {
					patches++
				}
			}
			for _, e := range s.Allow.To {
				if e.RelationshipDefinitionSelectorsPatch != nil {
					patches++
				}
			}
		}
	}
	fmt.Printf("before dehydration: components=%d relationships=%d selectors=%d patches=%d annotation=%d\n",
		compIDs, relIDs, selIDs, patches, ann)

	// the production step
	patterns.DehydratePattern(pf)

	b, err := encoding.Marshal(pf)
	if err != nil {
		fmt.Fprintln(os.Stderr, "MARSHAL FAILED:", err)
		os.Exit(3)
	}
	if err := os.WriteFile(out, b, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "write:", err)
		os.Exit(4)
	}
	fmt.Printf("dehydrated + marshalled -> %s (%d bytes)\n", out, len(b))
}
