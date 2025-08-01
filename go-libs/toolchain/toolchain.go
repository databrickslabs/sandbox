package toolchain

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/process"
)

func FromFileset(files fileset.FileSet, codegenPath *string) (*Toolchain, error) {
	var raw []byte
	var err error

	// Helper function to filter files and retrieve raw content
	getFileContent := func(filter string) ([]byte, error) {
		filteredFiles := files.Filter(filter)
		if len(filteredFiles) == 0 {
			return nil, fmt.Errorf("file not found in fileset: %s", filter)
		}
		return filteredFiles[0].Raw()
	}

	// Check if codegenPath is provided and retrieve content
	if codegenPath != nil && *codegenPath != "" {
		raw, err = getFileContent(*codegenPath)
		if err != nil {
			return nil, fmt.Errorf("provided 'codegen_path' does not exist in the project: %w", fs.ErrNotExist)
		}
	} else {
		raw, err = getFileContent(".codegen.json")
		if err != nil {
			return nil, fmt.Errorf("no .codegen.json found. %w", fs.ErrNotExist)
		}
	}

	// Unmarshal JSON content into dotCodegen struct
	var dc dotCodegen
	err = json.Unmarshal(raw, &dc)
	if err != nil {
		return nil, fmt.Errorf("unmarshal: %w", err)
	}
	return dc.Toolchain, nil
}

type dotCodegen struct {
	// code generation toolchain configuration
	Toolchain *Toolchain `json:"toolchain,omitempty"`
}

type Toolchain struct {
	Required       []string `json:"required"`
	PreSetup       []string `json:"pre_setup,omitempty"`
	PrependPath    string   `json:"prepend_path,omitempty"`
	AcceptancePath string   `json:"acceptance_path,omitempty"`
	Setup          []string `json:"setup,omitempty"`
	Test           []string `json:"test,omitempty"`
	PostGenerate   []string `json:"post_generate,omitempty"`
}

func (tc *Toolchain) runCmds(ctx context.Context, dir, prefix string, cmds []string) error {
	for _, cmd := range cmds {
		_, err := process.Background(ctx, []string{
			"bash", "-c", cmd,
		}, process.WithDir(dir))

		var processErr *process.ProcessError
		if errors.As(err, &processErr) {
			return fmt.Errorf("%s: %s", prefix, processErr.Stderr)
		} else if err != nil {
			return err
		}
	}
	return nil
}

func (tc *Toolchain) RunPrepare(ctx context.Context, dir string) (err error) {
	for _, required := range tc.Required {
		_, err := process.Background(ctx, []string{
			"bash", "-c", fmt.Sprintf("which %s", required),
		}, process.WithDir(dir))
		if err != nil {
			return fmt.Errorf("toolchain.required: %w", err)
		}
	}
	err = tc.runCmds(ctx, dir, "toolchain.pre_setup", tc.PreSetup)
	if err != nil {
		return err
	}
	ctx = tc.WithPath(ctx, dir)
	err = tc.runCmds(ctx, dir, "toolchain.setup", tc.Setup)
	if err != nil {
		return err
	}
	return nil
}

func (tc *Toolchain) WithPath(ctx context.Context, dir string) context.Context {
	if tc.PrependPath == "" {
		return ctx
	}
	// emulate virtualenv
	prependPath := filepath.Join(dir, tc.PrependPath)
	envPath, ok := env.Lookup(ctx, "PATH")
	if ok && strings.Contains(envPath, prependPath) {
		return ctx
	}
	return env.Set(ctx, "PATH", fmt.Sprintf("%s:%s", prependPath, env.Get(ctx, "PATH")))
}

func (tc *Toolchain) RunTest(ctx context.Context, dir string) (err error) {
	ctx = tc.WithPath(ctx, dir)
	err = tc.runCmds(ctx, dir, "toolchain.test", tc.Test)
	if err != nil {
		return err
	}
	return nil
}

func (tc *Toolchain) ForwardTests(ctx context.Context, dir string) (err error) {
	ctx = tc.WithPath(ctx, dir)
	for _, cmd := range tc.Test {
		err := process.Forwarded(ctx, []string{
			"bash", "-c", cmd,
		}, os.Stdin, os.Stdout, os.Stderr, process.WithDir(dir))
		var processErr *process.ProcessError
		if errors.As(err, &processErr) {
			return fmt.Errorf("unit tests: %s", processErr.Stderr)
		} else if err != nil {
			return err
		}
	}
	return nil
}
