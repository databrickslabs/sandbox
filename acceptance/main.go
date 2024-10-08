package main

import (
	"context"
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/databrickslabs/sandbox/acceptance/boilerplate"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/acceptance/notify"
	"github.com/databrickslabs/sandbox/acceptance/redaction"
	"github.com/databrickslabs/sandbox/acceptance/testenv"
	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/databrickslabs/sandbox/go-libs/slack"
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
	a := &acceptance{Boilerplate: b}
	alert, err := a.trigger(ctx)
	if err != nil {
		return fmt.Errorf("trigger: %w", err)
	}
	return a.notifyIfNeeded(ctx, alert)
}

type acceptance struct {
	*boilerplate.Boilerplate
}

func (a *acceptance) trigger(ctx context.Context) (*notify.Notification, error) {
	vaultURI := a.Action.GetInput("vault_uri")
	directory, project, err := a.getProject()
	if err != nil {
		return nil, fmt.Errorf("project: %w", err)
	}
	artifactDir, err := a.PrepareArtifacts()
	if err != nil {
		return nil, fmt.Errorf("prepare artifacts: %w", err)
	}
	defer os.RemoveAll(artifactDir)
	testEnv := testenv.NewWithGitHubOIDC(a.Action, vaultURI)
	loaded, err := testEnv.Load(ctx)
	if err != nil {
		return nil, fmt.Errorf("load: %w", err)
	}
	ctx, stop, err := loaded.Start(ctx)
	if err != nil {
		return nil, fmt.Errorf("start: %w", err)
	}
	defer stop()
	// make sure that test logs leave their artifacts somewhere we can pickup
	ctx = env.Set(ctx, ecosystem.LogDirEnv, artifactDir)
	redact := loaded.Redaction()
	report, err := a.runWithTimeout(ctx, redact, directory)
	if err != nil {
		return nil, fmt.Errorf("run: %w", err)
	}
	err = report.WriteReport(project, filepath.Join(artifactDir, "test-report.json"))
	if err != nil {
		return nil, fmt.Errorf("report: %w", err)
	}
	err = a.Upload(ctx, artifactDir)
	if err != nil {
		return nil, fmt.Errorf("upload artifact: %w", err)
	}
	// better be redacting twice, right?
	summary := redact.ReplaceAll(report.StepSummary())
	a.Action.AddStepSummary(summary)
	err = a.AddOrUpdateComment(ctx, summary)
	if err != nil {
		return nil, fmt.Errorf("comment: %w", err)
	}
	runUrl, err := a.RunURL(ctx)
	if err != nil {
		return nil, fmt.Errorf("run url: %w", err)
	}
	kvStoreURL, err := url.Parse(vaultURI)
	if err != nil {
		return nil, fmt.Errorf("vault uri: %w", err)
	}
	runName := strings.TrimSuffix(kvStoreURL.Host, ".vault.azure.net")
	return &notify.Notification{
		Project: project,
		Report:  report,
		Cloud:   loaded.Cloud(),
		RunName: runName,
		RunURL:  runUrl,
	}, nil
}

func (a *acceptance) runWithTimeout(
	ctx context.Context, redact redaction.Redaction, directory string,
) (ecosystem.TestReport, error) {
	timeoutRaw := a.Action.GetInput("timeout")
	if timeoutRaw == "" {
		timeoutRaw = "50m"
	}
	timeout, err := time.ParseDuration(timeoutRaw)
	if err != nil {
		return nil, fmt.Errorf("timeout: %w", err)
	}
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	// detect and run all tests
	report, err := ecosystem.RunAll(ctx, redact, directory)
	if err == nil || errors.Is(err, context.DeadlineExceeded) {
		return report, nil
	}
	return nil, fmt.Errorf("unknown: %w", err)
}

func (a *acceptance) notifyIfNeeded(ctx context.Context, alert *notify.Notification) error {
	slackWebhook := a.Action.GetInput("slack_webhook")
	createIssues := strings.ToLower(a.Action.GetInput("create_issues"))
	needsSlack := slackWebhook != ""
	needsIssues := createIssues == "true" || createIssues == "yes"
	needsNotification := needsSlack || needsIssues
	if !alert.Report.Pass() && needsNotification {
		if needsSlack {
			hook := slack.Webhook(slackWebhook)
			err := alert.ToSlack(hook)
			if err != nil {
				return fmt.Errorf("slack: %w", err)
			}
		}
		if needsIssues {
			for _, v := range alert.Report {
				if !v.Failed() {
					continue
				}
				err := a.CreateOrCommentOnIssue(ctx, github.NewIssue{
					Title:  fmt.Sprintf("Test failure: `%s`", v.Name),
					Body:   v.Summary(ecosystem.CommentMaxSize),
					Labels: []string{"bug"},
				})
				if err != nil {
					return fmt.Errorf("create issue: %w", err)
				}
			}
		}
	}
	return alert.Report.Failed()
}

func (a *acceptance) getProject() (string, string, error) {
	directory := a.Action.GetInput("directory")
	project := a.Action.GetInput("project")
	if project == "" {
		abs, err := filepath.Abs(directory)
		if err != nil {
			return "", "", fmt.Errorf("absolute path: %w", err)
		}
		project = filepath.Base(abs)
	}
	return directory, project, nil
}
