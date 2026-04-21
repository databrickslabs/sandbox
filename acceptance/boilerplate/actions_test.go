package boilerplate

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/sethvargo/go-githubactions"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestPrepareArtifacts_NoEventPath(t *testing.T) {
	b := &Boilerplate{
		context: &githubactions.GitHubContext{
			EventPath: "",
		},
	}
	dir, err := b.PrepareArtifacts()
	require.NoError(t, err)
	defer os.RemoveAll(dir)
	assert.DirExists(t, dir)
}

func TestPrepareArtifacts_WithEventPath(t *testing.T) {
	tmpDir := t.TempDir()
	eventFile := filepath.Join(tmpDir, "event.json")
	err := os.WriteFile(eventFile, []byte(`{"action":"opened"}`), 0644)
	require.NoError(t, err)

	b := &Boilerplate{
		context: &githubactions.GitHubContext{
			EventPath: eventFile,
		},
	}
	dir, err := b.PrepareArtifacts()
	require.NoError(t, err)
	defer os.RemoveAll(dir)

	assert.DirExists(t, dir)
	data, err := os.ReadFile(filepath.Join(dir, "event.json"))
	require.NoError(t, err)
	assert.Equal(t, `{"action":"opened"}`, string(data))
}

func TestPrepareArtifacts_MissingEventFile(t *testing.T) {
	b := &Boilerplate{
		context: &githubactions.GitHubContext{
			EventPath: "/nonexistent/event.json",
		},
	}
	_, err := b.PrepareArtifacts()
	assert.ErrorContains(t, err, "event")
}

func TestWorkflowRunName(t *testing.T) {
	b := &Boilerplate{
		context: &githubactions.GitHubContext{
			Workflow:  "CI",
			RunNumber: 42,
		},
	}
	assert.Equal(t, "CI #42", b.WorkflowRunName())
}

func TestTag(t *testing.T) {
	a := githubactions.New(githubactions.WithGetenv(func(key string) string {
		if key == "GITHUB_WORKFLOW_REF" {
			return "org/repo/.github/workflows/ci.yml@refs/heads/main"
		}
		return ""
	}))
	b := &Boilerplate{
		Action:   a,
		context:  &githubactions.GitHubContext{},
		ExtraTag: "extra",
	}
	tag := b.tag()
	assert.Contains(t, tag, "workflow:")
	assert.Contains(t, tag, "org/repo/.github/workflows/ci.yml@refs/heads/main")
	assert.Contains(t, tag, "extra")
}

func TestCurrentPullRequest_NilEvent(t *testing.T) {
	b := &Boilerplate{
		context: &githubactions.GitHubContext{
			Event: nil,
		},
	}
	_, err := b.currentPullRequest(t.Context())
	assert.ErrorContains(t, err, "missing actions event")
}

func TestCurrentPullRequest_NoPR(t *testing.T) {
	b := &Boilerplate{
		context: &githubactions.GitHubContext{
			Event: map[string]any{
				"action": "push",
			},
		},
	}
	pr, err := b.currentPullRequest(t.Context())
	require.NoError(t, err)
	assert.Nil(t, pr)
}

func TestCurrentPullRequest_WithPR(t *testing.T) {
	b := &Boilerplate{
		context: &githubactions.GitHubContext{
			Event: map[string]any{
				"pull_request": map[string]any{
					"number": float64(42),
					"title":  "test PR",
				},
			},
		},
	}
	pr, err := b.currentPullRequest(t.Context())
	require.NoError(t, err)
	require.NotNil(t, pr)
	assert.Equal(t, 42, pr.Number)
}
