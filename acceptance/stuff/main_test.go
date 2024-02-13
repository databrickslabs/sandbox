package main

import (
	"context"
	"testing"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/acceptance/redaction"
)

func TestXxx(t *testing.T) {
	ctx := context.Background()
	_, err := ecosystem.RunAll(ctx, redaction.Redaction{}, "/Users/serge.smertin/git/labs/ucx")
	if err != nil {
		logger.Errorf(ctx, "fail: %s", err)
		return
	}
}
