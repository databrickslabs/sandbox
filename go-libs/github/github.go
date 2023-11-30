package github

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/databricks/databricks-sdk-go/httpclient"
)

const gitHubAPI = "https://api.github.com"
const gitHubUserContent = "https://raw.githubusercontent.com"

// Placeholders to use as unique keys in context.Context.
var apiOverride int
var userContentOverride int

type GitHubClient struct {
	api *httpclient.ApiClient
	cfg *GitHubConfig
}

type GitHubConfig struct {
	GitHubTokenSource

	RetryTimeout       time.Duration
	HTTPTimeout        time.Duration
	InsecureSkipVerify bool
	DebugHeaders       bool
	DebugTruncateBytes int
	RateLimitPerSecond int

	transport http.RoundTripper
}

func NewClient(cfg *GitHubConfig) *GitHubClient {
	return &GitHubClient{
		api: httpclient.NewApiClient(httpclient.ClientConfig{
			Visitors: []httpclient.RequestVisitor{func(r *http.Request) error {
				token, err := cfg.Token()
				if err != nil {
					return fmt.Errorf("token: %w", err)
				}
				auth := fmt.Sprintf("%s %s", token.TokenType, token.AccessToken)
				r.Header.Set("Authorization", auth)
				return nil
			}},
			RetryTimeout:       cfg.RetryTimeout,
			HTTPTimeout:        cfg.HTTPTimeout,
			InsecureSkipVerify: cfg.InsecureSkipVerify,
			DebugHeaders:       cfg.DebugHeaders,
			DebugTruncateBytes: cfg.DebugTruncateBytes,
			RateLimitPerSecond: cfg.RateLimitPerSecond,
			Transport:          cfg.transport,
		}),
		cfg: cfg,
	}
}

func (c *GitHubClient) Versions(ctx context.Context, org, repo string) (Versions, error) {
	var releases Versions
	url := fmt.Sprintf("%s/repos/%s/%s/releases", gitHubAPI, org, repo)
	err := c.api.Do(ctx, "GET", url, httpclient.WithResponseUnmarshal(&releases))
	return releases, err
}

func (c *GitHubClient) GetRepo(ctx context.Context, org, name string) (repo Repo, err error) {
	url := fmt.Sprintf("%s/repos/%s/%s", gitHubAPI, org, name)
	err = c.api.Do(ctx, "GET", url, httpclient.WithResponseUnmarshal(&repo))
	return
}

func (c *GitHubClient) ListRepositories(ctx context.Context, org string) (Repositories, error) {
	var repos Repositories
	url := fmt.Sprintf("%s/users/%s/repos", gitHubAPI, org)
	err := c.api.Do(ctx, "GET", url, httpclient.WithResponseUnmarshal(&repos))
	return repos, err
}

func (c *GitHubClient) ListRuns(ctx context.Context, org, repo, workflow string) ([]workflowRun, error) {
	path := fmt.Sprintf("/repos/%s/%s/actions/workflows/%v.yml/runs", org, repo, workflow)
	var response struct {
		TotalCount   *int          `json:"total_count,omitempty"`
		WorkflowRuns []workflowRun `json:"workflow_runs,omitempty"`
	}
	err := c.api.Do(ctx, "GET", path, httpclient.WithResponseUnmarshal(&response))
	return response.WorkflowRuns, err
}

func WithApiOverride(ctx context.Context, override string) context.Context {
	return context.WithValue(ctx, &apiOverride, override)
}

func WithUserContentOverride(ctx context.Context, override string) context.Context {
	return context.WithValue(ctx, &userContentOverride, override)
}

var ErrNotFound = errors.New("not found")

func getBytes(ctx context.Context, method, url string, body io.Reader) ([]byte, error) {
	ao, ok := ctx.Value(&apiOverride).(string)
	if ok {
		url = strings.Replace(url, gitHubAPI, ao, 1)
	}
	uco, ok := ctx.Value(&userContentOverride).(string)
	if ok {
		url = strings.Replace(url, gitHubUserContent, uco, 1)
	}
	req, err := http.NewRequestWithContext(ctx, "GET", url, body)
	if err != nil {
		return nil, err
	}
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	if res.StatusCode == 404 {
		return nil, ErrNotFound
	}
	if res.StatusCode >= 400 {
		return nil, fmt.Errorf("github request failed: %s", res.Status)
	}
	defer res.Body.Close()
	return io.ReadAll(res.Body)
}

func httpGetAndUnmarshal(ctx context.Context, url string, response any) error {
	raw, err := getBytes(ctx, "GET", url, nil)
	if err != nil {
		return err
	}
	return json.Unmarshal(raw, response)
}
