package boilerplate

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/sethvargo/go-githubactions"
)

func New(ctx context.Context, opts ...githubactions.Option) (*boilerplate, error) {
	opts = append(opts, githubactions.WithGetenv(func(key string) string {
		return env.Get(ctx, key)
	}))
	a := githubactions.New(opts...)
	context, err := a.Context()
	if err != nil {
		return nil, err
	}
	logger.DefaultLogger = &actionsLogger{a}
	return &boilerplate{
		Action:  a,
		context: context,
		GitHub: github.NewClient(&github.GitHubConfig{
			GitHubTokenSource: github.GitHubTokenSource{},
		}),
		uploader: newUploader(ctx),
	}, nil
}

type boilerplate struct {
	Action   *githubactions.Action
	context  *githubactions.GitHubContext
	GitHub   *github.GitHubClient
	uploader *artifactUploader
}

func (a *boilerplate) PrepareArtifacts() (string, error) {
	tempDir, err := os.MkdirTemp(os.TempDir(), "artifacts-*")
	if err != nil {
		return "", fmt.Errorf("tmp: %w", err)
	}
	if a.context.EventPath == "" {
		return tempDir, nil
	}
	event, err := os.ReadFile(a.context.EventPath)
	if err != nil {
		return "", fmt.Errorf("event: %w", err)
	}
	err = os.WriteFile(filepath.Join(tempDir, "event.json"), event, 0600)
	if err != nil {
		return "", fmt.Errorf("copy: %w", err)
	}
	return tempDir, nil
}

func (a *boilerplate) Upload(ctx context.Context, folder string) error {
	res, err := a.uploader.Upload(ctx, "acceptance", folder)
	if err != nil {
		return fmt.Errorf("upload: %w", err)
	}
	logger.Infof(ctx, "Uploaded artifact: %s", res.ArtifactID)
	return nil
}

func (a *boilerplate) RunURL(ctx context.Context) (string, error) {
	org, repo := a.context.Repo()
	workflowJobs := a.GitHub.ListWorkflowJobs(ctx, org, repo, a.context.RunID)
	for workflowJobs.HasNext(ctx) {
		job, err := workflowJobs.Next(ctx)
		if err != nil {
			return "", err
		}
		if job.RunnerName == a.Action.Getenv("RUNNER_NAME") {
			url := fmt.Sprintf("%s/%s/actions/runs/%d/job/%d", // ?pr=56
				a.context.ServerURL, a.context.Repository, a.context.RunID, job.ID)
			return url, nil
		}
	}
	return "", fmt.Errorf("id not found for current run: %s", a.context.Job)
}

func (a *boilerplate) tag() string {
	// The ref path to the workflow. For example,
	// octocat/hello-world/.github/workflows/my-workflow.yml@refs/heads/my_branch.
	return fmt.Sprintf("\n<!-- workflow:%s -->", a.Action.Getenv("GITHUB_WORKFLOW_REF"))
}

func (a *boilerplate) taggedComment(ctx context.Context, body string) (string, error) {
	runUrl, err := a.RunURL(ctx)
	if err != nil {
		return "", fmt.Errorf("run url: %w", err)
	}
	return fmt.Sprintf("%s\n\n<sub>Running from [%s #%d](%s)</sub>%s",
		body, a.context.Workflow, a.context.RunNumber, runUrl, a.tag()), nil
}

func (a *boilerplate) currentPullRequest(ctx context.Context) (*github.PullRequest, error) {
	if a.context.Event == nil {
		return nil, fmt.Errorf("missing actions event")
	}
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

func (a *boilerplate) Comment(ctx context.Context, commentText string) error {
	pr, err := a.currentPullRequest(ctx)
	if err != nil {
		return fmt.Errorf("pr: %w", err)
	}
	tag := a.tag()
	org, repo := a.context.Repo()
	it := a.GitHub.GetIssueComments(ctx, org, repo, pr.Number)
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
		_, err = a.GitHub.UpdateIssueComment(ctx, org, repo, comment.ID, text)
		return err
	}
	text, err := a.taggedComment(ctx, commentText)
	if err != nil {
		return fmt.Errorf("text: %w", err)
	}
	_, err = a.GitHub.CreateIssueComment(ctx, org, repo, pr.Number, text)
	if err != nil {
		return fmt.Errorf("new comment: %w", err)
	}
	return nil
}
