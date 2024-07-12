package main

import (
	"context"
	"testing"

	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/stretchr/testify/assert"
)

func TestXxx(t *testing.T) {
	t.Skip()
	ctx := context.Background()
	ctx = env.Set(ctx, "INPUT_DIRECTORY", "../go-libs")
	err := run(ctx)
	assert.NoError(t, err)
}
