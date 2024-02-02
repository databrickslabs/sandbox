package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
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

func (a *acceptance) runURL(ctx context.Context) (string, error) {
	org, repo := a.context.Repo()
	workflowJobs := a.gh.ListWorkflowJobs(ctx, org, repo, a.context.RunID)
	for workflowJobs.HasNext(ctx) {
		job, err := workflowJobs.Next(ctx)
		if err != nil {
			return "", err
		}
		if job.RunnerName == a.action.Getenv("RUNNER_NAME") {
			url := fmt.Sprintf("%s/%s/actions/runs/%d/job/%d", // ?pr=56
				a.context.ServerURL, a.context.Repository, a.context.RunID, job.ID)
			return url, nil
		}
	}
	return "", fmt.Errorf("id not found for current run: %s", a.context.Job)
}

func (a *acceptance) tag() string {
	// The ref path to the workflow. For example,
	// octocat/hello-world/.github/workflows/my-workflow.yml@refs/heads/my_branch.
	return fmt.Sprintf("\n<!-- workflow:%s -->", a.action.Getenv("GITHUB_WORKFLOW_REF"))
}

func (a *acceptance) taggedComment(ctx context.Context, body string) (string, error) {
	runUrl, err := a.runURL(ctx)
	if err != nil {
		return "", fmt.Errorf("run url: %w", err)
	}
	return fmt.Sprintf("%s\n<sub>Running from [%s #%d](%s)</sub>%s",
		body, a.context.Workflow, a.context.RunNumber, runUrl, a.tag()), nil
}

func (a *acceptance) currentPullRequest(ctx context.Context) (*github.PullRequest, error) {
	raw, err := json.MarshalIndent(a.context.Event, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("marshall: %w", err)
	}
	var event struct {
		PullRequest *github.PullRequest `json:"pull_request"`
	}
	err = json.Unmarshal(raw, &event)
	if err != nil {
		return nil, fmt.Errorf("unmarshall: %w", err)
	}
	return event.PullRequest, nil
}

func (a *acceptance) comment(ctx context.Context, commentText string) error {
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
		text, err := a.taggedComment(ctx, commentText)
		if err != nil {
			return fmt.Errorf("text: %w", err)
		}
		_, err = a.gh.UpdateIssueComment(ctx, org, repo, comment.ID, text)
		return err
	}
	text, err := a.taggedComment(ctx, commentText)
	if err != nil {
		return fmt.Errorf("text: %w", err)
	}
	_, err = a.gh.CreateIssueComment(ctx, org, repo, pr.Number, text)
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
	directory := a.action.GetInput("directory")
	report, err := ecosystem.RunAll(ctx, directory)
	if err != nil {
		return err
	}
	return a.comment(ctx, report.StepSummary())

	// also - there's OIDC integration:
	// a.GetIDToken(ctx, "api://AzureADTokenExchange")
}

func main() {
	err := run(context.Background())
	if err != nil {
		githubactions.Fatalf("failed: %s", err)
	}
}
