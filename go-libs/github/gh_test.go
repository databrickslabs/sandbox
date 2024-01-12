package github_test

import (
	"context"
	"fmt"
	"sync"
	"testing"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/github"
)

func init() {
	logger.DefaultLogger = &logger.SimpleLogger{
		Level: logger.LevelDebug,
	}
}

func TestXxx(t *testing.T) {
	gh := github.NewClient(&github.GitHubConfig{
		DebugHeaders: true,
	})
	var wg sync.WaitGroup
	ctx := context.Background()
	for i := 0; i < 1000; i++ {
		wg.Add(1)
		n := fmt.Sprintf("triggering-retry-after-header-%d", i)
		go func() {
			gh.GetRepo(ctx, "nfx", n)
			wg.Done()
		}()
	}
	wg.Wait()
	_, err := gh.GetRepo(ctx, "nfx", "nnnnnonexisting")
	t.Logf("x: %s", err)
}
