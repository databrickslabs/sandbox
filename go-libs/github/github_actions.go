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
		TotalCount   *int          `json:"total_count,omitempty"`
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
