package boilerplate

import (
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"strings"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/sethvargo/go-githubactions"
)

func New(ctx context.Context, opts ...githubactions.Option) (*Boilerplate, error) {
	opts = append(opts, githubactions.WithGetenv(func(key string) string {
		return env.Get(ctx, key)
	}))
	a := githubactions.New(opts...)
	context, err := a.Context()
	if err != nil {
		return nil, err
	}
	logger.DefaultLogger = &actionsLogger{a}
	return &Boilerplate{
		Action:  a,
		context: context,
		GitHub: github.NewClient(&github.GitHubConfig{
			GitHubTokenSource: github.GitHubTokenSource{},
		}),
		uploader: newUploader(ctx),
	}, nil
}

type Boilerplate struct {
	Action   *githubactions.Action
	context  *githubactions.GitHubContext
	GitHub   *github.GitHubClient
	uploader *artifactUploader
	ExtraTag string
}

func (a *Boilerplate) PrepareArtifacts() (string, error) {
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

func (a *Boilerplate) Upload(ctx context.Context, folder string) error {
	charset := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	suffix := make([]byte, 12)
	for i := range suffix {
		suffix[i] = charset[rand.Intn(len(suffix))]
	}
	res, err := a.uploader.Upload(ctx, fmt.Sprintf("acceptance-%s", suffix), folder)
	if err != nil {
		return fmt.Errorf("upload: %w", err)
	}
	logger.Debugf(ctx, "Uploaded artifact: %s", res.ArtifactID)
	return nil
}

func (a *Boilerplate) RunURL(ctx context.Context) (string, error) {
	org, repo := a.context.Repo()
	logger.Debugf(ctx, "List jobs for current run id '%s'", a.context.RunID)
	workflowJobs := a.GitHub.ListWorkflowJobs(ctx, org, repo, a.context.RunID)
	for workflowJobs.HasNext(ctx) {
		job, err := workflowJobs.Next(ctx)
		if err != nil {
			return "", err
		}
		logger.Debugf(ctx, "Check if job id '%s' with runnner '%s' matches RUNNER_NAME '%s'", 
			job.ID, job.RunnerName, a.Action.Getenv("RUNNER_NAME"))
		if job.RunnerName == a.Action.Getenv("RUNNER_NAME") {
			url := fmt.Sprintf("%s/%s/actions/runs/%d/job/%d", // ?pr=56
				a.context.ServerURL, a.context.Repository, a.context.RunID, job.ID)
			logger.Debugf(ctx, "Found job id '%s' with url '%s'", job.ID, url)
			return url, nil
		}
	}
	return "", fmt.Errorf("no matching job found for current run id %s, job %s", a.context.RunID, a.context.Job)
}

func (a *Boilerplate) CreateOrCommentOnIssue(ctx context.Context, newIssue github.NewIssue) error {
	org, repo := a.context.Repo()
	it := a.GitHub.ListRepositoryIssues(ctx, org, repo, &github.ListIssues{
		State: "open",
	})
	created := map[string]int{}
	for it.HasNext(ctx) {
		issue, err := it.Next(ctx)
		if err != nil {
			return fmt.Errorf("issue: %w", err)
		}
		created[issue.Title] = issue.Number
	}
	// with the tagged comment, which has the workflow ref, we can link to the run
	body, err := a.taggedComment(ctx, newIssue.Body)
	if err != nil {
		return fmt.Errorf("tagged comment: %w", err)
	}
	number, ok := created[newIssue.Title]
	if ok {
		_, err = a.GitHub.CreateIssueComment(ctx, org, repo, number, body)
		if err != nil {
			return fmt.Errorf("new comment: %w", err)
		}
		return nil
	}
	issue, err := a.GitHub.CreateIssue(ctx, org, repo, github.NewIssue{
		Title:     newIssue.Title,
		Assignees: newIssue.Assignees,
		Labels:    newIssue.Labels,
		Body:      body,
	})
	if err != nil {
		return fmt.Errorf("new issue: %w", err)
	}
	logger.Infof(ctx, "Created new issue: https://github.com/%s/%s/issues/%d", org, repo, issue.Number)
	return nil
}

func (a *Boilerplate) tag() string {
	// The ref path to the workflow. For example,
	// octocat/hello-world/.github/workflows/my-workflow.yml@refs/heads/my_branch.
	return fmt.Sprintf("\n<!-- workflow:%s %s -->", a.Action.Getenv("GITHUB_WORKFLOW_REF"), a.ExtraTag)
}

func (a *Boilerplate) taggedComment(ctx context.Context, body string) (string, error) {
	runUrl, err := a.RunURL(ctx)
	if err != nil {
		return "", fmt.Errorf("run url: %w", err)
	}
	return fmt.Sprintf("%s\n\n<sub>Running from [%s](%s)</sub>%s",
		body, a.WorkflowRunName(), runUrl, a.tag()), nil
}

func (a *Boilerplate) WorkflowRunName() string {
	return fmt.Sprintf("%s #%d", a.context.Workflow, a.context.RunNumber)
}

func (a *Boilerplate) currentPullRequest(ctx context.Context) (*github.PullRequest, error) {
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

func (a *Boilerplate) AddOrUpdateComment(ctx context.Context, commentText string) error {
	pr, err := a.currentPullRequest(ctx)
	if err != nil {
		return fmt.Errorf("pr: %w", err)
	}
	if pr == nil {
		logger.Infof(ctx, "running from a nightly workflow, no pull request to comment")
		return nil
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
