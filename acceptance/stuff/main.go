package main

import (
	"context"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/acceptance/redaction"
)

func init() {
	logger.DefaultLogger = &logger.SimpleLogger{
		Level: logger.LevelDebug,
	}
}

func main() {
	ctx := context.Background()
	_, err := ecosystem.RunAll(ctx, redaction.Redaction{}, "/Users/serge.smertin/git/labs/ucx")
	if err != nil {
		logger.Errorf(ctx, "fail: %s", err)
		return
	}
}
