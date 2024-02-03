package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/databrickslabs/sandbox/acceptance/boilerplate"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/process"
	"github.com/sethvargo/go-githubactions"
)

func run(ctx context.Context, opts ...githubactions.Option) error {
	b, err := boilerplate.New(ctx)
	if err != nil {
		return fmt.Errorf("boilerplate: %w", err)
	}
	directory := b.Action.GetInput("directory")
	project := b.Action.GetInput("project")
	if project == "" {
		abs, err := filepath.Abs(directory)
		if err != nil {
			return fmt.Errorf("absolute path: %w", err)
		}
		project = filepath.Base(abs)
	}
	artifactDir, err := b.PrepareArtifacts()
	if err != nil {
		return fmt.Errorf("prepare artifacts: %w", err)
	}
	defer os.RemoveAll(artifactDir)
	// make sure that test logs leave their artifacts somewhere we can pickup
	ctx = env.Set(ctx, ecosystem.LogDirEnv, artifactDir)
	// detect and run all tests
	report, testErr := ecosystem.RunAll(ctx, directory)
	err = report.WriteReport(project, filepath.Join(artifactDir, "test-report.json"))
	if err != nil {
		return errors.Join(testErr, err)
	}
	summary := report.StepSummary()
	var processErr *process.ProcessError
	if errors.As(testErr, &processErr) {
		summary = fmt.Sprintf("%s\n<details><summary>%s</summary>%s</details>", summary, processErr.Stdout, processErr.Stderr)
	}
	err = b.Comment(ctx, summary)
	if err != nil {
		return errors.Join(testErr, err)
	}
	err = b.Upload(ctx, artifactDir)
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
