package boilerplate

import (
	"bytes"
	"context"
	"testing"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/sethvargo/go-githubactions"
	"github.com/stretchr/testify/assert"
)

func TestActionsLogger_Enabled(t *testing.T) {
	a := githubactions.New()
	l := &actionsLogger{a}
	assert.True(t, l.Enabled(context.Background(), logger.LevelDebug))
	assert.True(t, l.Enabled(context.Background(), logger.LevelInfo))
	assert.True(t, l.Enabled(context.Background(), logger.LevelWarn))
	assert.True(t, l.Enabled(context.Background(), logger.LevelError))
}

func TestActionsLogger_Methods(t *testing.T) {
	// Use a buffer to capture output from the actions logger
	var buf bytes.Buffer
	a := githubactions.New(githubactions.WithWriter(&buf))
	l := &actionsLogger{a}
	ctx := context.Background()

	l.Tracef(ctx, "trace %s", "msg")
	l.Debugf(ctx, "debug %s", "msg")
	l.Infof(ctx, "info %s", "msg")
	l.Warnf(ctx, "warn %s", "msg")
	l.Errorf(ctx, "error %s", "msg")

	output := buf.String()
	assert.Contains(t, output, "debug msg") // Tracef maps to Debugf
	assert.Contains(t, output, "info msg")
	assert.Contains(t, output, "warn msg")
	assert.Contains(t, output, "error msg")
}
