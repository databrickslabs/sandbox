package main

import (
	"context"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
)

func init() {
	logger.DefaultLogger = &logger.SimpleLogger{
		Level: logger.LevelDebug,
	}
}

func main() {
	ctx := context.Background()
	_, err := ecosystem.RunAll(ctx, "/Users/serge.smertin/git/labs/ucx")
	if err != nil {
		logger.Errorf(ctx, "fail: %s", err)
		return
	}
}
