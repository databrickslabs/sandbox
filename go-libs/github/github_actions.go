package github

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databricks/databricks-sdk-go/retries"
	"golang.org/x/oauth2"
)

type ListArtifacts struct {
	TotalCount int64      `json:"total_count"`
	Artifacts  []Artifact `json:"artifacts"`
}

type Artifact struct {
	ID                 int64      `json:"id"`
	NodeID             string     `json:"node_id,omitempty"`
	Name               string     `json:"name"`
	SizeInBytes        int64      `json:"size_in_bytes"`
	ArchiveDownloadURL string     `json:"archive_download_url"`
	Expired            bool       `json:"expired,omitempty"`
	CreatedAt          time.Time  `json:"created_at,omitempty"`
	ExpiresAt          *time.Time `json:"expires_at,omitempty"`

	// only ID, repository ID, head_repository_id, head_branch, and head_sha available
	WorflowRun *WorkflowRun `json:"workflow_run,omitempty"`
}

type ListWorkflowRunsOptions struct {
	Actor  string `url:"actor,omitempty"`
	Branch string `url:"branch,omitempty"`

	// Returns workflow run triggered by the event you specify. For example, push, pull_request or issue.
	Event string `url:"event,omitempty"`

	// Can be one of: completed, action_required, cancelled, failure, neutral, skipped, stale,
	// success, timed_out, in_progress, queued, requested, waiting, pending
	Status string `url:"status,omitempty"`

	// Returns workflow runs created within the given date-time range.
	// See https://docs.github.com/search-github/getting-started-with-searching-on-github/understanding-the-search-syntax#query-for-dates
	Created string `url:"created,omitempty"`
	PageOptions
}

type WorkflowRuns struct {
	TotalCount   int           `json:"total_count,omitempty"`
	WorkflowRuns []WorkflowRun `json:"workflow_runs,omitempty"`
}

type WorkflowRun struct {
	ID                 int64         `json:"id,omitempty"`
	Name               string        `json:"name,omitempty"`
	NodeID             string        `json:"node_id,omitempty"`
	HeadBranch         string        `json:"head_branch,omitempty"`
	HeadSHA            string        `json:"head_sha,omitempty"`
	RunNumber          int           `json:"run_number,omitempty"`
	RunAttempt         int           `json:"run_attempt,omitempty"`
	Event              string        `json:"event,omitempty"`
	Status             string        `json:"status,omitempty"`
	Conclusion         string        `json:"conclusion,omitempty"`
	WorkflowID         int64         `json:"workflow_id,omitempty"`
	CheckSuiteID       int64         `json:"check_suite_id,omitempty"`
	CheckSuiteNodeID   string        `json:"check_suite_node_id,omitempty"`
	URL                string        `json:"url,omitempty"`
	HTMLURL            string        `json:"html_url,omitempty"`
	PullRequests       []PullRequest `json:"pull_requests,omitempty"`
	CreatedAt          time.Time     `json:"created_at,omitempty"`
	UpdatedAt          *time.Time    `json:"updated_at,omitempty"`
	RunStartedAt       *time.Time    `json:"run_started_at,omitempty"`
	JobsURL            string        `json:"jobs_url,omitempty"`
	LogsURL            string        `json:"logs_url,omitempty"`
	CheckSuiteURL      string        `json:"check_suite_url,omitempty"`
	ArtifactsURL       string        `json:"artifacts_url,omitempty"`
	CancelURL          string        `json:"cancel_url,omitempty"`
	RerunURL           string        `json:"rerun_url,omitempty"`
	PreviousAttemptURL string        `json:"previous_attempt_url,omitempty"`
	WorkflowURL        string        `json:"workflow_url,omitempty"`
	Repository         Repo          `json:"repository,omitempty"`
	HeadRepository     Repo          `json:"head_repository,omitempty"`
	Actor              User          `json:"actor,omitempty"`
}

type Workflow struct {
	ID        int64      `json:"id,omitempty"`
	NodeID    string     `json:"node_id,omitempty"`
	Name      string     `json:"name,omitempty"`
	Path      string     `json:"path,omitempty"`
	State     string     `json:"state,omitempty"`
	CreatedAt time.Time  `json:"created_at,omitempty"`
	UpdatedAt *time.Time `json:"updated_at,omitempty"`
	URL       string     `json:"url,omitempty"`
	HTMLURL   string     `json:"html_url,omitempty"`
	BadgeURL  string     `json:"badge_url,omitempty"`
}

type Workflows struct {
	TotalCount int        `json:"total_count,omitempty"`
	Workflows  []Workflow `json:"workflows,omitempty"`
}

type TaskStep struct {
	Name        string    `json:"name,omitempty"`
	Status      string    `json:"status,omitempty"`
	Conclusion  string    `json:"conclusion,omitempty"`
	Number      int64     `json:"number,omitempty"`
	StartedAt   time.Time `json:"started_at,omitempty"`
	CompletedAt time.Time `json:"completed_at,omitempty"`
}

type WorkflowJob struct {
	ID              int64      `json:"id,omitempty"`
	RunID           int64      `json:"run_id,omitempty"`
	RunURL          string     `json:"run_url,omitempty"`
	NodeID          string     `json:"node_id,omitempty"`
	HeadSHA         string     `json:"head_sha,omitempty"`
	URL             string     `json:"url,omitempty"`
	HTMLURL         string     `json:"html_url,omitempty"`
	Status          string     `json:"status,omitempty"`
	Conclusion      string     `json:"conclusion,omitempty"`
	StartedAt       time.Time  `json:"started_at,omitempty"`
	CompletedAt     time.Time  `json:"completed_at,omitempty"`
	Name            string     `json:"name,omitempty"`
	Steps           []TaskStep `json:"steps,omitempty"`
	CheckRunURL     string     `json:"check_run_url,omitempty"`
	Labels          []string   `json:"labels,omitempty"`
	RunnerID        int64      `json:"runner_id,omitempty"`
	RunnerName      string     `json:"runner_name,omitempty"`
	RunnerGroupID   int64      `json:"runner_group_id,omitempty"`
	RunnerGroupName string     `json:"runner_group_name,omitempty"`
}

type Jobs struct {
	TotalCount int           `json:"total_count,omitempty"`
	Jobs       []WorkflowJob `json:"jobs,omitempty"`
}

const ghApi = "https://api.github.com"

type GitHubActionsWorkflow struct {
	Connect   GitHubTokenSource
	Workflows []string
	Timeout   time.Duration
}

type workflowRun struct {
	ID     int64  `json:"id"`
	Name   string `json:"name"`
	Status string `json:"status"` // waiting, in_progress, completed
	ApiURL string `json:"url,omitempty"`
	WebURL string `json:"html_url,omitempty"`
}

func (g *GitHubActionsWorkflow) Wait(ctx context.Context) error {
	client := oauth2.NewClient(ctx, &g.Connect)
	return retries.Wait(ctx, g.Timeout, func() *retries.Err {
		var inProgress int
		refs := []string{}
		for _, ref := range g.Workflows {
			runs, err := g.listRuns(client, ref)
			if err != nil {
				return retries.Halt(err)
			}
			for _, run := range runs {
				if run.Status == "in_progress" {
					refs = append(refs, fmt.Sprintf("%s#%d", ref, run.ID))
					inProgress++
				}
			}
		}
		if inProgress > 0 {
			names := strings.Join(refs, ", ")
			msg := fmt.Sprintf("workflows in progress: %d (%s)", inProgress, names)
			logger.Infof(ctx, msg)
			return retries.Continues(msg)
		}
		return nil
	})
}

func (g *GitHubActionsWorkflow) listRuns(client *http.Client, ref string) ([]workflowRun, error) {
	//ref: org/repo/workflow, e.g. databrickslabs/ucx/acceptance
	split := strings.SplitN(ref, "/", 3)
	path := fmt.Sprintf("/repos/%s/%s/actions/workflows/%v.yml/runs", split[0], split[1], split[2])
	var response struct {
		TotalCount   int           `json:"total_count,omitempty"`
		WorkflowRuns []workflowRun `json:"workflow_runs,omitempty"`
	}
	err := g.get(client, path, &response)
	return response.WorkflowRuns, err
}

func (g *GitHubActionsWorkflow) get(client *http.Client, path string, v any) error {
	resp, err := client.Get(ghApi + path)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return json.NewDecoder(resp.Body).Decode(&v)
}
