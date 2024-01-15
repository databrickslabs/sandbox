package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"

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
		getenv: os.Getenv,
	}, nil
}

type acceptance struct {
	action  *githubactions.Action
	context *githubactions.GitHubContext
	gh      *github.GitHubClient
	getenv  func(key string) string
}

func (a *acceptance) runURL() string {
	return fmt.Sprintf("%s/%s/actions/runs/%d/job/%s", // ?pr=56
		a.context.ServerURL, a.context.Repository, a.context.RunID, a.context.Job)
}

func (a *acceptance) tag() string {
	// The ref path to the workflow. For example,
	// octocat/hello-world/.github/workflows/my-workflow.yml@refs/heads/my_branch.
	return fmt.Sprintf("\n<!-- workflow:%s -->", a.getenv("GITHUB_WORKFLOW_REF"))
}

func (a *acceptance) taggedComment(body string) string {
	// GITHUB_WORKFLOW_REF
	return fmt.Sprintf("%s\n---\n<sub>Running from [%s #%d](%s)</sub>%s",
		body, a.context.Workflow, a.context.RunNumber, a.runURL(), a.tag())
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
	tag := a.tag()
	org, repo := a.context.Repo()
	it := a.gh.GetIssueComments(ctx, org, repo, pr.Number)
	for it.HasNext(ctx) {
		comment, err := it.Next(ctx)
		if err != nil {
			return fmt.Errorf("comment: %w", err)
		}
		if !strings.Contains(comment.Body, tag) {
			continue
		}
		_, err = a.gh.UpdateIssueComment(ctx, org, repo, comment.ID, a.taggedComment("Updated comment"))
		return err
	}
	_, err = a.gh.CreateIssueComment(ctx, org, repo, pr.Number, a.taggedComment("New comment"))
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
