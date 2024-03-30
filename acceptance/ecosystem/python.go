// This file integrates with PyTest
//
// See https://docs.pytest.org/en/latest/reference/reference.html#hook-reference

package ecosystem

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"time"

	_ "embed"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/redaction"
	"github.com/databrickslabs/sandbox/go-libs/toolchain"
	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/process"
	"github.com/nxadm/tail"
)

//go:embed pytest_collect.py
var pyTestCollect string

//go:embed pytest_run.py
var pyTestRun string

//go:embed pytest_run_one.py
var pyTestRunOne string

var ErrNotImplemented = errors.New("not implemented")

type pyTestRunner struct {
	files fileset.FileSet
}

func (r pyTestRunner) Detect() bool {
	return r.files.Exists("pyproject.toml", "pytest")
}

type pyContext struct {
	ctx     context.Context
	redact  redaction.Redaction
	root    string
	venv    string
	logfile string
}

func (py *pyContext) start(args []string) error {
	reader, writer, err := os.Pipe()
	if err != nil {
		return err
	}
	defer writer.Close()
	defer reader.Close()
	openFlags := os.O_CREATE | os.O_TRUNC | os.O_WRONLY
	tee, err := os.OpenFile(py.logfile, openFlags, 0644)
	if err != nil {
		return fmt.Errorf("pytest.log: %w", err)
	}
	defer tee.Close()
	go py.redact.Copy(tee, reader)
	return process.Forwarded(py.ctx, args,
		nil, writer, writer,
		process.WithDir(py.root))
}

func (py *pyContext) Start(script string, reply *localHookServer) chan error {
	errs := make(chan error)
	go func() {
		py.ctx = env.Set(py.ctx, "REPLY_URL", reply.URL())
		err := py.start([]string{
			filepath.Join(py.venv, "python"), "-c", script,
		})
		var processErr *process.ProcessError
		if errors.As(err, &processErr) {
			logger.Warnf(py.ctx, "collect: %s", processErr.Stderr)
		}
		errs <- err
	}()
	return errs
}

func (r pyTestRunner) prepare(ctx context.Context, redact redaction.Redaction, logfile string) (*pyContext, error) {
	tc, err := toolchain.FromFileset(r.files)
	if err != nil {
		return nil, fmt.Errorf("detect: %w", err)
	}
	testRoot := r.files.Root()
	err = tc.RunPrepare(ctx, testRoot)
	if err != nil {
		return nil, fmt.Errorf("prepared: %w", err)
	}
	prepend, err := filepath.Abs(filepath.Join(testRoot, tc.PrependPath))
	if err != nil {
		return nil, fmt.Errorf("prepend: %w", err)
	}
	ctx = tc.WithPath(ctx, testRoot)
	if tc.AcceptancePath != "" {
		testRoot = filepath.Join(testRoot, tc.AcceptancePath)
	}
	logDir := env.Get(ctx, LogDirEnv)
	return &pyContext{
		ctx:     ctx,
		redact:  redact,
		root:    testRoot,
		venv:    prepend,
		logfile: filepath.Join(logDir, logfile),
	}, nil
}

func (r pyTestRunner) ListAll(ctx context.Context) []string {
	ctx, cancel := context.WithTimeout(ctx, 1*time.Minute)
	defer cancel()
	reply := newLocalHookServer(ctx)
	defer reply.Close()
	py, err := r.prepare(ctx, redaction.Redaction{}, "pytest-collect.out")
	if err != nil {
		logger.Warnf(ctx, ".codegen.json: %s", err)
		return nil
	}
	errs := py.Start(pyTestCollect, reply)
	var out []string
	err = reply.Unmarshal(&out)
	if err != nil {
		logger.Warnf(ctx, "callback: %s", err)
		return nil
	}
	err = <-errs
	if err != nil {
		logger.Warnf(ctx, "background: %s", err)
		return nil
	}
	return out
}

var nonAlphanumRegex = regexp.MustCompile(`[^a-zA-Z0-9-]+`)

func (r pyTestRunner) RunOne(ctx context.Context, redact redaction.Redaction, one string) error {
	logfile := fmt.Sprintf("pytest-%s.out", nonAlphanumRegex.ReplaceAllString(one, "_"))
	py, err := r.prepare(ctx, redact, logfile)
	if err != nil {
		return fmt.Errorf(".codegen.json: %w", err)
	}
	tailer, err := tail.TailFile(py.logfile, tail.Config{Follow: true})
	if err != nil {
		return err
	}
	go func() {
		for line := range tailer.Lines {
			os.Stdout.WriteString(line.Text + "\n")
		}
	}()
	py.ctx = env.Set(py.ctx, "TEST_FILTER", one)
	return py.start([]string{
		filepath.Join(py.venv, "python"), "-c", pyTestRunOne,
	})
}

func (r pyTestRunner) RunAll(ctx context.Context, redact redaction.Redaction) (TestReport, error) {
	ctx, cancel := context.WithTimeout(ctx, 1*time.Hour)
	defer cancel()
	reply := newLocalHookServer(ctx)
	defer reply.Close()
	py, err := r.prepare(ctx, redact, "pytest-all.out")
	if err != nil {
		return nil, fmt.Errorf(".codegen.json: %w", err)
	}
	report := TestReport{}
	errs := py.Start(pyTestRun, reply)
	for {
		select {
		case <-ctx.Done():
			return report, err
		case err := <-errs:
			if err != nil {
				err = fmt.Errorf("pytest: %w", err)
			}
			return report, err
		case err := <-reply.errCh:
			if err != nil {
				err = fmt.Errorf("hook: %w", err)
			}
			return report, err
		case raw := <-reply.hookCh:
			var result TestResult
			err = json.Unmarshal(raw, &result)
			if err != nil {
				return nil, fmt.Errorf("reply: %w", err)
			}
			result.Time = time.Now()
			logger.Infof(ctx, "%s", result)
			result.Output = redact.ReplaceAll(result.Output)
			report = append(report, result)
		}
	}
}

type localHookServer struct {
	server *httptest.Server
	ctx    context.Context
	errCh  chan error
	hookCh chan []byte
}

func newLocalHookServer(ctx context.Context) *localHookServer {
	hookCh := make(chan []byte)
	errCh := make(chan error)
	return &localHookServer{
		server: httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer r.Body.Close()
			raw, err := io.ReadAll(r.Body)
			if err != nil {
				errCh <- err
				return
			}
			hookCh <- raw
		})),
		hookCh: hookCh,
		errCh:  errCh,
		ctx:    ctx,
	}
}

func (cb *localHookServer) URL() string {
	return cb.server.URL
}

func (cb *localHookServer) Close() {
	cb.server.Close()
}

func (cb *localHookServer) Unmarshal(v any) error {
	select {
	case <-cb.ctx.Done():
		return cb.ctx.Err()
	case err := <-cb.errCh:
		return err
	case raw := <-cb.hookCh:
		return json.Unmarshal(raw, v)
	}
}
