package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/boilerplate"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/sethvargo/go-githubactions"
)

func init() {
	logger.DefaultLogger = &logger.SimpleLogger{
		Level: logger.LevelDebug,
	}
}

func run(ctx context.Context, opts ...githubactions.Option) error {
	b, err := boilerplate.New(ctx)
	if err != nil {
		return fmt.Errorf("boilerplate: %w", err)
	}
	directory := b.Action.GetInput("directory")
	project := b.Action.GetInput("project")
	artifactDir, err := b.PrepareArtifacts()
	if err != nil {
		return fmt.Errorf("prepare artifacts: %w", err)
	}
	defer os.RemoveAll(artifactDir)
	report, testErr := ecosystem.RunAll(ctx, directory)
	err = report.WriteReport(project, filepath.Join(artifactDir, "test-report.json"))
	if err != nil {
		return errors.Join(testErr, err)
	}
	err = b.Comment(ctx, report.StepSummary())
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
