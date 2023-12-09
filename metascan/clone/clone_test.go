package clone

import (
	"context"
	"path/filepath"
	"testing"

	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/git"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/databrickslabs/sandbox/metascan/inventory"
	"github.com/stretchr/testify/require"
)

func TestDiscoversSandbox(t *testing.T) {
	ctx := context.Background()
	home, _ := env.UserHomeDir(ctx)
	dir := filepath.Join(home, ".databricks/labs/metascan/cache/databricks/terraform-databricks-examples")

	fs, err := fileset.RecursiveChildren(dir)
	require.NoError(t, err)

	checkout, err := git.NewCheckout(ctx, dir)
	require.NoError(t, err)

	clone := &Clone{
		Inventory: inventory.Item{
			Org:       "databricks",
			Repo:      "terraform-databricks-examples",
			IsSandbox: true,
		},
		Repo: github.Repo{
			Name:   "terraform-databricks-examples",
			Topics: []string{"terraform", "modules"},
		},
		Git:     checkout,
		FileSet: fs,
	}

	metadatas, err := clone.Metadatas(ctx)
	require.NoError(t, err)

	require.True(t, len(metadatas) > 0)
}
