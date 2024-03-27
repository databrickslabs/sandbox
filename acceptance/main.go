package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/databrickslabs/sandbox/acceptance/boilerplate"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/acceptance/notify"
	"github.com/databrickslabs/sandbox/acceptance/testenv"
	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/sethvargo/go-githubactions"
)

func run(ctx context.Context, opts ...githubactions.Option) error {
	b, err := boilerplate.New(ctx)
	if err != nil {
		return fmt.Errorf("boilerplate: %w", err)
	}
	timeoutRaw := b.Action.GetInput("timeout")
	if timeoutRaw == "" {
		timeoutRaw = "1h"
	}
	timeout, err := time.ParseDuration(timeoutRaw)
	if err != nil {
		return fmt.Errorf("timeout: %w", err)
	}
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	vaultURI := b.Action.GetInput("vault_uri")
	directory := b.Action.GetInput("directory")
	project := b.Action.GetInput("project")
	if project == "" {
		abs, err := filepath.Abs(directory)
		if err != nil {
			return fmt.Errorf("absolute path: %w", err)
		}
		project = filepath.Base(abs)
	}
	artifactDir, err := b.PrepareArtifacts()
	if err != nil {
		return fmt.Errorf("prepare artifacts: %w", err)
	}
	defer os.RemoveAll(artifactDir)
	testEnv := testenv.NewWithGitHubOIDC(b.Action, vaultURI)
	loaded, err := testEnv.Load(ctx)
	if err != nil {
		return fmt.Errorf("load: %w", err)
	}
	ctx, stop, err := loaded.Start(ctx)
	if err != nil {
		return fmt.Errorf("start: %w", err)
	}
	defer stop()
	// make sure that test logs leave their artifacts somewhere we can pickup
	ctx = env.Set(ctx, ecosystem.LogDirEnv, artifactDir)
	redact := loaded.Redaction()
	// detect and run all tests
	report, err := ecosystem.RunAll(ctx, redact, directory)
	if err != nil {
		return fmt.Errorf("unknown: %w", err)
	}
	err = report.WriteReport(project, filepath.Join(artifactDir, "test-report.json"))
	if err != nil {
		return fmt.Errorf("report: %w", err)
	}
	// better be redacting twice, right?
	summary := redact.ReplaceAll(report.StepSummary())
	b.Action.AddStepSummary(summary)
	err = b.Comment(ctx, summary)
	if err != nil {
		return fmt.Errorf("comment: %w", err)
	}
	err = b.Upload(ctx, artifactDir)
	if err != nil {
		return fmt.Errorf("upload artifact: %w", err)
	}
	slackWebhook := b.Action.GetInput("slack_webhook")
	createIssues := strings.ToLower(b.Action.GetInput("create_issues"))
	needsSlack := slackWebhook != ""
	needsIssues := createIssues == "true" || createIssues == "yes"
	needsNotification := needsSlack || needsIssues
	if !report.Pass() && needsNotification {
		runUrl, err := b.RunURL(ctx)
		if err != nil {
			return fmt.Errorf("run url: %w", err)
		}
		alert := notify.Notification{
			Project: project,
			Report:  report,
			Cloud:   loaded.Cloud(),
			RunName: b.WorkflowRunName(),
			WebHook: slackWebhook,
			RunURL:  runUrl,
		}
		if needsSlack {
			err = alert.ToSlack()
			if err != nil {
				return fmt.Errorf("slack: %w", err)
			}
		}
		if needsIssues {
			for _, v := range report {
				if !v.Failed() {
					continue
				}
				err = b.CreateIssueIfNotOpen(ctx, github.NewIssue{
					Title: fmt.Sprintf("Test failure: `%s`", v.Name),
					Body:  v.Summary(),
					Labels: []string{"bug"},
				})
				if err != nil {
					return fmt.Errorf("create issue: %w", err)
				}
			}
		}
	}
	return report.Failed()
}

func main() {
	err := run(context.Background())
	if err != nil {
		githubactions.Fatalf("failed: %s", err)
	}
}
