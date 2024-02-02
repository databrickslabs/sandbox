package main

import (
	"context"

	"github.com/databrickslabs/sandbox/acceptance/boilerplate"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/sethvargo/go-githubactions"
)

func run(ctx context.Context, opts ...githubactions.Option) error {
	b, err := boilerplate.New(ctx)
	if err != nil {
		return err
	}
	directory := b.Action.GetInput("directory")
	report, err := ecosystem.RunAll(ctx, directory)
	if err != nil {
		return err
	}
	return b.Comment(ctx, report.StepSummary())

	// also - there's OIDC integration:
	// a.GetIDToken(ctx, "api://AzureADTokenExchange")
}

func main() {
	err := run(context.Background())
	if err != nil {
		githubactions.Fatalf("failed: %s", err)
	}
}
