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
	"path/filepath"
	"time"

	_ "embed"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/toolchain"
	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/process"
)

//go:embed pytest_collect.py
var pyTestCollect string

//go:embed pytest_run.py
var pyTestRun string

var ErrNotImplemented = errors.New("not implemented")

type pyTestRunner struct{}

func (r pyTestRunner) Detect(files fileset.FileSet) bool {
	return files.Exists("pyproject.toml", "pytest")
}

type pyContext struct {
	ctx    context.Context
	binary string
	root   string
}

func (py *pyContext) Start(script string, reply *localHookServer) chan error {
	errs := make(chan error)
	go func() {
		_, err := process.Background(py.ctx,
			[]string{py.binary, "-c", script},
			process.WithDir(py.root),
			process.WithEnv("REPLY_URL", reply.URL()))
		var processErr *process.ProcessError
		if errors.As(err, &processErr) {
			logger.Warnf(py.ctx, "collect: %s", processErr.Stderr)
		}
		errs <- err
	}()
	return errs
}

func (r pyTestRunner) prepare(ctx context.Context, files fileset.FileSet) (*pyContext, error) {
	tc, err := toolchain.FromFileset(files)
	if err != nil {
		return nil, fmt.Errorf("detect: %w", err)
	}
	err = tc.RunPrepare(ctx, files.Root())
	if err != nil {
		return nil, fmt.Errorf("prepared: %w", err)
	}
	ctx = tc.WithPath(ctx, files.Root())

	venvPython := filepath.Join(files.Root(), tc.PrependPath, "python")
	testRoot := files.Root()
	if tc.AcceptancePath != "" {
		testRoot = filepath.Join(files.Root(), tc.AcceptancePath)
	}
	return &pyContext{
		ctx:    ctx,
		binary: venvPython,
		root:   testRoot,
	}, nil
}

func (r pyTestRunner) ListAll(ctx context.Context, files fileset.FileSet) []string {
	ctx, cancel := context.WithTimeout(ctx, 1*time.Minute)
	defer cancel()
	reply := newLocalHookServer(ctx)
	defer reply.Close()
	py, err := r.prepare(ctx, files)
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

func (r pyTestRunner) RunOne(ctx context.Context, files fileset.FileSet, one string) error {
	return ErrNotImplemented
}

func (r pyTestRunner) RunAll(ctx context.Context, files fileset.FileSet) (TestReport, error) {
	ctx, cancel := context.WithTimeout(ctx, 1*time.Minute)
	defer cancel()
	reply := newLocalHookServer(ctx)
	defer reply.Close()
	py, err := r.prepare(ctx, files)
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
			return report, err
		case err := <-reply.errCh:
			return report, err
		case raw := <-reply.hookCh:
			var result TestResult
			err = json.Unmarshal(raw, &result)
			if err != nil {
				return nil, fmt.Errorf("reply: %w", err)
			}
			logger.Infof(ctx, "[%v] %s", result.Pass, result.Name)
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
