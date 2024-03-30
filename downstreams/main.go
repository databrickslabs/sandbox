package main

import (
	"context"
	"fmt"

	"github.com/databrickslabs/sandbox/acceptance/boilerplate"
	"github.com/databrickslabs/sandbox/go-libs/linkdev"
	"github.com/sethvargo/go-githubactions"
)

func main() {
	err := run(context.Background())
	if err != nil {
		githubactions.Fatalf("failed: %s", err)
	}
}

func run(ctx context.Context, opts ...githubactions.Option) error {
	b, err := boilerplate.New(ctx, opts...)
	if err != nil {
		return fmt.Errorf("boilerplate: %w", err)
	}
	repo := linkdev.Repo{
		Org:  b.Action.GetInput("org"),
		Repo: b.Action.GetInput("repo"),
	}
	b.ExtraTag = repo.Repo
	err = repo.Retest(ctx, ".")
	if err != nil {
		message := fmt.Sprintf(
			"This PR breaks backwards compatibility for %s/%s downstream. "+
				"See build logs for more details.", repo.Org, repo.Repo)
		err = b.AddOrUpdateComment(ctx, message)
		if err != nil {
			return fmt.Errorf("comment: %w", err)
		}
		return fmt.Errorf("run test: %w", err)
	}
	return nil
}
