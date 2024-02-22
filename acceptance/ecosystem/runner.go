package ecosystem

import (
	"context"
	"errors"
	"fmt"
	"os/exec"
	"time"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/redaction"
	"github.com/databrickslabs/sandbox/go-libs/fileset"
)

const LogDirEnv = "DATABRICKS_LABS_LOG_DIR"

type TestRunner interface {
	Detect() bool
	ListAll(ctx context.Context) []string
	RunOne(ctx context.Context, redact redaction.Redaction, one string) error
	RunAll(ctx context.Context, redact redaction.Redaction) (TestReport, error)
}

func New(folder string) (TestRunner, error) {
	files, err := fileset.RecursiveChildren(folder)
	if err != nil {
		return nil, fmt.Errorf("fileset: %w", err)
	}
	var runners = []TestRunner{
		goTestRunner{files},
		pyTestRunner{files},
	}
	for _, v := range runners {
		if v.Detect() {
			return v, nil
		}
	}
	return nil, fmt.Errorf("no supported ecosystem detected")
}

func RunAll(ctx context.Context, redact redaction.Redaction, folder string) (TestReport, error) {
	runner, err := New(folder)
	if err != nil {
		return nil, fmt.Errorf("ecosystem: %w", err)
	}
	started := time.Now()
	report, err := runner.RunAll(ctx, redact)
	// 0 - all passed, 1 - some failed, 2 - interrupted
	// See: https://docs.pytest.org/en/4.6.x/usage.html
	// See: https://github.com/golang/go/issues/25989
	var exitErr *exec.ExitError
	if errors.As(err, &exitErr) && exitErr.ExitCode() > 1 {
		return nil, exitErr
	}
	// sequential de-flake loop
	for i, result := range report {
		if result.Pass || result.Skip {
			continue
		}
		logger.Infof(ctx, "⛑️ re-running: %s", result.Name)
		rerunErr := runner.RunOne(ctx, redact, result.Name)
		if rerunErr == nil {
			report[i].Flaky = true
			report[i].Pass = true
			logger.Warnf(ctx, "🥴 flaky test detected: %s", result.Name)
		}
	}
	logger.Infof(ctx, "%s, took %s", report, time.Since(started).Round(time.Second))
	return report, nil
}
