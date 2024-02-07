package fixtures

import (
	"context"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/logger"
)

func init() {
	databricks.WithProduct("integration-tests", databricks.Version())
	logDir, ok := os.LookupEnv("DATABRICKS_LABS_LOG_DIR")
	if !ok {
		// we're debugging from IDE
		logger.DefaultLogger = &logger.SimpleLogger{
			Level: logger.LevelDebug,
		}
		return
	}
	filename := filepath.Join(logDir, "go-slog.json")
	file, err := os.OpenFile(filename, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil {
		panic(err)
	}
	// we don't close file descriptor, as this is test-binary-wide logger
	installSlogJSON(file)
}

func installSlogJSON(w io.Writer) {
	handler := slog.NewJSONHandler(w, &slog.HandlerOptions{
		Level: slog.LevelDebug,
	})
	slogger := slog.New(handler)
	logger.DefaultLogger = &slogAdapter{
		// TODO: figure out GitHub Pull Request context propagation
		slogger.With("global", true),
	}
}

// slogAdapter makes an slog.Logger usable with the Databricks SDK.
type slogAdapter struct {
	*slog.Logger
}

func (s *slogAdapter) Enabled(ctx context.Context, level logger.Level) bool {
	switch level {
	case logger.LevelTrace:
		// Note: slog doesn't have a default trace level.
		// An application can define their own fine grained levels
		// and use those here, if needed.
		return s.Logger.Enabled(ctx, slog.LevelDebug)
	case logger.LevelDebug:
		return s.Logger.Enabled(ctx, slog.LevelDebug)
	case logger.LevelInfo:
		return s.Logger.Enabled(ctx, slog.LevelInfo)
	case logger.LevelWarn:
		return s.Logger.Enabled(ctx, slog.LevelWarn)
	case logger.LevelError:
		return s.Logger.Enabled(ctx, slog.LevelError)
	default:
		return true
	}
}

func (s *slogAdapter) Tracef(ctx context.Context, format string, v ...any) {
	s.DebugContext(ctx, fmt.Sprintf(format, v...))
}

func (s *slogAdapter) Debugf(ctx context.Context, format string, v ...any) {
	s.DebugContext(ctx, fmt.Sprintf(format, v...))
}

func (s *slogAdapter) Infof(ctx context.Context, format string, v ...any) {
	s.InfoContext(ctx, fmt.Sprintf(format, v...))
}

func (s *slogAdapter) Warnf(ctx context.Context, format string, v ...any) {
	s.WarnContext(ctx, fmt.Sprintf(format, v...))
}

func (s *slogAdapter) Errorf(ctx context.Context, format string, v ...any) {
	s.ErrorContext(ctx, fmt.Sprintf(format, v...))
}
