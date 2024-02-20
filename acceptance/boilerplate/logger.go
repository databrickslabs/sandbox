package boilerplate

import (
	"context"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/sethvargo/go-githubactions"
)

type actionsLogger struct {
	a *githubactions.Action
}

func (l *actionsLogger) Enabled(ctx context.Context, level logger.Level) bool {
	return true
}

func (l *actionsLogger) Tracef(ctx context.Context, format string, v ...any) {
	l.a.Debugf(format, v...)
}

func (l *actionsLogger) Debugf(ctx context.Context, format string, v ...any) {
	l.a.Debugf(format, v...)
}

func (l *actionsLogger) Infof(ctx context.Context, format string, v ...any) {
	l.a.Infof(format, v...)
}

func (l *actionsLogger) Warnf(ctx context.Context, format string, v ...any) {
	l.a.Warningf(format, v...)
}

func (l *actionsLogger) Errorf(ctx context.Context, format string, v ...any) {
	l.a.Errorf(format, v...)
}
