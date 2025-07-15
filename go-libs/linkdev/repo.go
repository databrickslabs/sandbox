package linkdev

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/git"
	"github.com/databrickslabs/sandbox/go-libs/process"
	"github.com/databrickslabs/sandbox/go-libs/toolchain"
)

type Repo struct {
	Org  string `json:"org"`
	Repo string `json:"repo"`
}

func (r Repo) CloneTo(ctx context.Context, dir string) (*git.Checkout, error) {
	if r.Org == "" {
		return nil, fmt.Errorf("org is required")
	}
	if r.Repo == "" {
		return nil, fmt.Errorf("repo is required")
	}
	cloneURL := fmt.Sprintf("https://github.com/%s/%s.git", r.Org, r.Repo)
	return git.LazyClone(ctx, cloneURL, dir)
}

func (r Repo) tempClone(ctx context.Context) (*git.Checkout, func() error, error) {
	tmp := filepath.Join(os.TempDir(), fmt.Sprintf("gh-%s-%s-%d", r.Org, r.Repo, time.Now().Unix()))
	checkout, err := r.CloneTo(ctx, tmp)
	if err != nil {
		return nil, nil, fmt.Errorf("cloning %s: %w", r.Repo, err)
	}
	return checkout, func() error {
		return os.RemoveAll(tmp)
	}, nil
}

func (r Repo) TemporaryFileset(ctx context.Context) (fileset.FileSet, func() error, error) {
	checkout, cleanup, err := r.tempClone(ctx)
	if err != nil {
		return nil, nil, err
	}
	files, err := fileset.RecursiveChildren(checkout.Dir())
	if err != nil {
		return nil, nil, fmt.Errorf("listing files: %w", err)
	}
	return files, cleanup, nil
}

func (r Repo) Retest(ctx context.Context, upstreamFolder string) error {
	downstreamFiles, _, err := r.TemporaryFileset(ctx)
	if err != nil {
		return fmt.Errorf("fileset: %w", err)
	}
	// defer cleanup()
	tc, err := toolchain.FromFileset(downstreamFiles, nil)
	if err != nil {
		return fmt.Errorf("toolchain: %w", err)
	}
	err = tc.RunPrepare(ctx, downstreamFiles.Root())
	if err != nil {
		return fmt.Errorf("prepare: %w", err)
	}
	// add the current virtual environment to $PATH
	ctx = tc.WithPath(ctx, downstreamFiles.Root())
	upstreamAbsolute, err := filepath.Abs(upstreamFolder)
	if err != nil {
		return fmt.Errorf("absolute path: %w", err)
	}
	err = r.flipUpstream(ctx, upstreamAbsolute, tc, downstreamFiles)
	if err != nil {
		return fmt.Errorf("flip: %w", err)
	}
	return tc.ForwardTests(ctx, downstreamFiles.Root())
}

func (r Repo) flipUpstream(
	ctx context.Context,
	upstreamDir string,
	tc *toolchain.Toolchain,
	downstream fileset.FileSet,
) error {
	isPython := downstream.Has("pyproject.toml") || downstream.Has("setup.py")
	if !isPython {
		return fmt.Errorf("only Python projects are supported for now")
	}
	// See https://pip.pypa.io/en/stable/reference/requirements-file-format/
	pip := "pip"
	if tc.PrependPath != "" {
		pip = filepath.Join(tc.PrependPath, "pip")
	}
	_, err := process.Background(ctx, []string{
		pip, "install", "--force-reinstall", "--editable", upstreamDir,
	}, process.WithDir(downstream.Root()))
	if err != nil {
		return fmt.Errorf("replace: %w", err)
	}
	return nil
}
