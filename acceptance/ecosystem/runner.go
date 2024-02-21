package ecosystem

import (
	"context"
	"fmt"

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
	return runner.RunAll(ctx, redact)
}
