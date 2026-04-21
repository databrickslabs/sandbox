package ecosystem

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNew_NoSupportedEcosystem(t *testing.T) {
	dir := t.TempDir()
	_, err := New(dir)
	assert.ErrorContains(t, err, "no supported ecosystem detected")
}

func TestNew_DetectsGo(t *testing.T) {
	dir := t.TempDir()
	err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module example.com/test\n\ngo 1.21\n"), 0644)
	require.NoError(t, err)
	runner, err := New(dir)
	require.NoError(t, err)
	assert.NotNil(t, runner)
}

func TestNew_DetectsPython(t *testing.T) {
	dir := t.TempDir()
	err := os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte("[tool.pytest]\n"), 0644)
	require.NoError(t, err)
	runner, err := New(dir)
	require.NoError(t, err)
	assert.NotNil(t, runner)
}

func TestNew_InvalidFolder(t *testing.T) {
	_, err := New("/nonexistent/folder/that/does/not/exist")
	assert.Error(t, err)
}

func TestNew_PrefersGoOverPython(t *testing.T) {
	dir := t.TempDir()
	err := os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module example.com/test\n\ngo 1.21\n"), 0644)
	require.NoError(t, err)
	err = os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte("[tool.pytest]\n"), 0644)
	require.NoError(t, err)
	runner, err := New(dir)
	require.NoError(t, err)
	// Go runner should be detected first
	assert.IsType(t, goTestRunner{}, runner)
}
