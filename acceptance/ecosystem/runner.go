package ecosystem

import (
	"context"
	"fmt"

	"github.com/databrickslabs/sandbox/go-libs/fileset"
)

const LogDirEnv = "DATABRICKS_LABS_LOG_DIR" 

type TestRunner interface {
	Detect(files fileset.FileSet) bool
	ListAll(ctx context.Context, files fileset.FileSet) []string
	RunOne(ctx context.Context, files fileset.FileSet, one string) error
	RunAll(ctx context.Context, files fileset.FileSet) (TestReport, error)
}

var runners = []TestRunner{
	GoTestRunner{},
	pyTestRunner{},
}

func RunAll(ctx context.Context, folder string) (TestReport, error) {
	files, err := fileset.RecursiveChildren(folder)
	if err != nil {
		return nil, fmt.Errorf("fileset: %w", err)
	}
	var runner TestRunner
	for _, v := range runners {
		if v.Detect(files) {
			runner = v
		}
	}
	if runner == nil {
		return nil, fmt.Errorf("no supported ecosystem detected")
	}
	return runner.RunAll(ctx, files)
}
