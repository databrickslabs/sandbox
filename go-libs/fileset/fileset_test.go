package fileset_test

import (
	"path/filepath"
	"testing"

	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/stretchr/testify/assert"
)

func TestRoot(t *testing.T) {
	fs, err := fileset.RecursiveChildren(".")
	assert.NoError(t, err)

	abs, err := filepath.Abs(".")
	assert.NoError(t, err)

	assert.Equal(t, abs, fs.Root())
}
