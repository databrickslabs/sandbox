package todos

import (
	"context"
	"testing"

	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/stretchr/testify/assert"
)

func TestXXX(t *testing.T) {
	t.SkipNow()
	ctx := context.Background()

	gh := github.NewClient(&github.GitHubConfig{})
	f, err := New(ctx, gh, "/Users/serge.smertin/git/labs/remorph")
	assert.NoError(t, err)

	err = f.CreateIssues(ctx)
	assert.NoError(t, err)
}
