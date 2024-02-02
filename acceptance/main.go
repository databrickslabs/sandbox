package main

import (
	"context"
	"errors"

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
	report, testErr := ecosystem.RunAll(ctx, directory)
	err = b.Comment(ctx, report.StepSummary())
	if err != nil {
		return errors.Join(testErr, err)
	}
	return testErr
	// also - there's OIDC integration:
	// a.GetIDToken(ctx, "api://AzureADTokenExchange")
}

func main() {
	err := run(context.Background())
	if err != nil {
		githubactions.Fatalf("failed: %s", err)
	}
}
