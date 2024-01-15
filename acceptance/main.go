package main

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/sethvargo/go-githubactions"
)

func New(opts ...githubactions.Option) (*acceptance, error) {
	a := githubactions.New(opts...)
	// token, err := a.GetIDToken(context.Background(), "")
	// if err != nil {
	// 	return nil, fmt.Errorf("oidc: %w", err)
	// }
	context, err := a.Context()
	if err != nil {
		return nil, err
	}
	return &acceptance{
		action:  a,
		context: context,
		gh: github.NewClient(&github.GitHubConfig{
			GitHubTokenSource: github.GitHubTokenSource{},
		}),
	}, nil
}

type acceptance struct {
	action  *githubactions.Action
	context *githubactions.GitHubContext
	gh      *github.GitHubClient
}

func (a *acceptance) currentPullRequest(ctx context.Context) (*github.PullRequest, error) {
	raw, err := json.MarshalIndent(a.context.Event, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("marshall: %w", err)
	}
	// fmt.Fprintf(os.Stdout, "b64: %s", base64.StdEncoding.EncodeToString(raw))
	var event struct {
		PullRequest *github.PullRequest `json:"pull_request"`
	}
	err = json.Unmarshal(raw, &event)
	if err != nil {
		return nil, fmt.Errorf("unmarshall: %w", err)
	}
	return event.PullRequest, nil
}

func (a *acceptance) comment(ctx context.Context) error {
	pr, err := a.currentPullRequest(ctx)
	if err != nil {
		return fmt.Errorf("pr: %w", err)
	}
	me, err := a.gh.CurrentUser(ctx)
	if err != nil {
		return fmt.Errorf("current user: %w", err)
	}
	org, repo := a.context.Repo()
	it := a.gh.GetIssueComments(ctx, org, repo, pr.Number)
	for it.HasNext(ctx) {
		comment, err := it.Next(ctx)
		if err != nil {
			return fmt.Errorf("comment: %w", err)
		}
		if comment.User.Login != me.Login {
			continue
		}
		_, err = a.gh.UpdateIssueComment(ctx, org, repo, comment.ID, "updated comment")
		return err
	}
	_, err = a.gh.CreateIssueComment(ctx, org, repo, pr.Number, "Test from acceptance action")
	if err != nil {
		return fmt.Errorf("new comment: %w", err)
	}
	return nil
}

func run(ctx context.Context) error {
	a, err := New()
	if err != nil {
		return err
	}
	return a.comment(ctx)
	// also - there's OIDC integration:
	// a.GetIDToken(ctx, "api://AzureADTokenExchange")
}

func main() {
	err := run(context.Background())
	if err != nil {
		githubactions.Fatalf("failed: %s", err)
	}
}
