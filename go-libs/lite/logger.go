package lite

import (
	"context"
	"fmt"
	"io"
	"log/slog"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/fatih/color"
)

type remappingHandler struct {
	slog.Handler
	overrides map[slog.Level]slog.Level
}

func (r *remappingHandler) Enabled(ctx context.Context, level slog.Level) bool {
	newLevel, ok := r.overrides[level]
	if ok {
		return r.Handler.Enabled(ctx, newLevel)
	}
	return r.Handler.Enabled(ctx, level)
}

func (r *remappingHandler) Handle(ctx context.Context, rec slog.Record) error {
	newLevel, ok := r.overrides[rec.Level]
	if ok {
		rec.Level = newLevel
	}
	return r.Handler.Handle(ctx, rec)
}

type friendlyHandler struct {
	slog.Handler
	w     io.Writer
	attrs []slog.Attr
}

var (
	levelTrace = color.New(color.FgYellow).Sprint("TRACE")
	levelDebug = color.New(color.FgYellow).Sprint("DEBUG")
	levelInfo  = color.New(color.FgGreen).Sprintf("%5s", "INFO")
	levelWarn  = color.New(color.FgMagenta).Sprintf("%5s", "WARN")
	levelError = color.New(color.FgRed).Sprint("ERROR")
)

func (l *friendlyHandler) coloredLevel(rec slog.Record) string {
	switch rec.Level {
	case -8:
		return levelTrace
	case slog.LevelDebug:
		return levelDebug
	case slog.LevelInfo:
		return levelInfo
	case slog.LevelWarn:
		return levelWarn
	case slog.LevelError:
		return levelError
	}
	return ""
}

func (l *friendlyHandler) Handle(ctx context.Context, rec slog.Record) error {
	t := fmt.Sprintf("%02d:%02d", rec.Time.Hour(), rec.Time.Minute())
	attrs := ""
	rec.AddAttrs(l.attrs...)
	rec.Attrs(func(a slog.Attr) bool {
		attrs += fmt.Sprintf(" %s%s%s",
			color.CyanString(a.Key),
			color.CyanString("="),
			color.YellowString(a.Value.String()))
		return true
	})
	msg := fmt.Sprintf("%s %s %s%s\n",
		color.MagentaString(t),
		l.coloredLevel(rec),
		rec.Message,
		attrs)
	_, err := l.w.Write([]byte(msg))
	return err
}

func (l *friendlyHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	return &friendlyHandler{
		Handler: l.Handler.WithAttrs(attrs),
		w:       l.w,
		attrs:   attrs,
	}
}

func (l *friendlyHandler) WithGroup(name string) slog.Handler {
	// TODO: this is not so correct implementation, but is fine for now
	return &friendlyHandler{
		Handler: l.Handler.WithGroup(name),
		w:       l.w,
		attrs:   []slog.Attr{slog.String("group", name)},
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
