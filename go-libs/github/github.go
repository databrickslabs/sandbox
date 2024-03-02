package github

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/databricks/databricks-sdk-go/common"
	"github.com/databricks/databricks-sdk-go/httpclient"
	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/google/go-querystring/query"
)

const gitHubAPI = "https://api.github.com"

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

	transport http.RoundTripper
}

func NewClient(cfg *GitHubConfig) *GitHubClient {
	// No more than 900 points per minute are allowed for REST API endpoints
	// See https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
	return &GitHubClient{
		api: httpclient.NewApiClient(httpclient.ClientConfig{
			Visitors: []httpclient.RequestVisitor{func(r *http.Request) error {
				token, err := cfg.Token()
				if err != nil {
					return fmt.Errorf("token: %w", err)
				}
				// we can also support anonymous calls to GH
				if token.AccessToken != "" {
					auth := fmt.Sprintf("%s %s", token.TokenType, token.AccessToken)
					r.Header.Set("Authorization", auth)
				}
				return nil
			}},
			ErrorMapper: func(ctx context.Context, rw common.ResponseWrapper) error {
				err := httpclient.DefaultErrorMapper(ctx, rw)
				if err == nil {
					return nil
				}
				var ghErr Error
				httpErr, ok := err.(*httpclient.HttpError)
				if !ok {
					return err
				}
				jsonErr := json.Unmarshal([]byte(httpErr.Message), &ghErr)
				if jsonErr != nil {
					return fmt.Errorf("json: %w: %w", jsonErr, httpErr)
				}
				ghErr.HttpError = httpErr
				now := time.Now().Local()
				var rateLimitResetUTC, retryAfter int64
				fmt.Sscanf(rw.Response.Header.Get("X-Ratelimit-Reset"), "%d", &rateLimitResetUTC)
				resetsIn := time.Duration(rateLimitResetUTC - now.UTC().Unix())
				ghErr.rateLimitReset = now.Add(time.Second * resetsIn)
				fmt.Sscanf(rw.Response.Header.Get("Retry-After"), "%d", &retryAfter)
				ghErr.retryAfter = time.Second * time.Duration(retryAfter)
				fmt.Sscanf(rw.Response.Header.Get("X-Ratelimit-Remaining"), "%d", &ghErr.rateLimitRemaining)
				return &ghErr
			},
			ErrorRetriable: func(ctx context.Context, err error) bool {
				ghErr, ok := err.(*Error)
				if !ok {
					return httpclient.DefaultErrorRetriable(ctx, err)
				}
				if ghErr.retryAfter > 0 {
					time.Sleep(ghErr.retryAfter)
					return true
				}
				return false
			},
			RetryTimeout:       cfg.RetryTimeout,
			HTTPTimeout:        cfg.HTTPTimeout,
			InsecureSkipVerify: cfg.InsecureSkipVerify,
			DebugHeaders:       cfg.DebugHeaders,
			DebugTruncateBytes: cfg.DebugTruncateBytes,
			Transport:          cfg.transport,
			RateLimitPerSecond: 10,
		}),
		cfg: cfg,
	}
}

func (c *GitHubClient) Versions(ctx context.Context, org, repo string) listing.Iterator[Release] {
	url := fmt.Sprintf("%s/repos/%s/%s/releases", gitHubAPI, org, repo)
	return paginator[Release, string](ctx, c, url, &PageOptions{}, func(r Release) string {
		return r.Version
	})
}

type CreateReleaseRequest struct {
	TagName                string `json:"tag_name,omitempty"`
	Name                   string `json:"name,omitempty"`
	Body                   string `json:"body,omitempty"`
	Draft                  bool   `json:"draft,omitempty"`
	Prerelease             bool   `json:"prerelease,omitempty"`
	GenerateReleaseNotes   bool   `json:"generate_release_notes,omitempty"`
	DiscussionCategoryName string `json:"discussion_category_name,omitempty"`
}

func (c *GitHubClient) CreateRelease(ctx context.Context, org, repo string, req CreateReleaseRequest) (*Release, error) {
	var res Release
	url := fmt.Sprintf("%s/repos/%s/%s/releases", gitHubAPI, org, repo)
	err := c.api.Do(ctx, "POST", url,
		httpclient.WithRequestData(req),
		httpclient.WithResponseUnmarshal(&res))
	return &res, err
}

func (c *GitHubClient) GetRepo(ctx context.Context, org, name string) (repo Repo, err error) {
	path := fmt.Sprintf("%s/repos/%s/%s", gitHubAPI, org, name)
	err = c.api.Do(ctx, "GET", path, httpclient.WithResponseUnmarshal(&repo))
	return
}

func (c *GitHubClient) ListRepositories(ctx context.Context, org string) listing.Iterator[Repo] {
	path := fmt.Sprintf("%s/users/%s/repos", gitHubAPI, org)
	return paginator[Repo, string](ctx, c, path, &PageOptions{}, func(r Repo) string {
		return r.SshURL
	})
}

func (c *GitHubClient) ListRepositoryIssues(ctx context.Context, org, repo string, req *ListIssues) listing.Iterator[Issue] {
	path := fmt.Sprintf("%s/repos/%s/%s/issues", gitHubAPI, org, repo)
	return paginator[Issue, int64](ctx, c, path, req, func(i Issue) int64 {
		return i.ID
	})
}

func (c *GitHubClient) ListWorkflows(ctx context.Context, org, repo string) listing.Iterator[Workflow] {
	path := fmt.Sprintf("%s/repos/%s/%s/actions/workflows", gitHubAPI, org, repo)
	return rawPaginator[Workflow, Workflows, int64](ctx, c, path, &PageOptions{}, func(w Workflows) []Workflow {
		return w.Workflows
	}, func(w Workflow) int64 {
		return w.ID
	})
}

func (c *GitHubClient) ListWorkflowRuns(ctx context.Context, org, repo string, opts *ListWorkflowRunsOptions) listing.Iterator[WorkflowRun] {
	path := fmt.Sprintf("%s/repos/%s/%s/actions/runs", gitHubAPI, org, repo)
	return rawPaginator[WorkflowRun, WorkflowRuns, int64](ctx, c, path, opts, func(wr WorkflowRuns) []WorkflowRun {
		return wr.WorkflowRuns
	}, func(wr WorkflowRun) int64 {
		return wr.ID
	})
}

func (c *GitHubClient) ListArtifacts(ctx context.Context, org, repo string) listing.Iterator[Artifact] {
	path := fmt.Sprintf("%s/repos/%s/%s/actions/artifacts", gitHubAPI, org, repo)
	return rawPaginator[Artifact, ListArtifacts, int64](ctx, c, path, &PageOptions{}, func(la ListArtifacts) []Artifact {
		return la.Artifacts
	}, func(a Artifact) int64 {
		return a.ID
	})
}

func (c *GitHubClient) GetWorkflowRunLogs(ctx context.Context, org, repo string, runID int64) (*bytes.Buffer, error) {
	var location string
	path := fmt.Sprintf("%s/repos/%v/%v/actions/runs/%v/logs", gitHubAPI, org, repo, runID)
	err := c.api.Do(ctx, "GET", path, httpclient.WithResponseHeader("Location", &location))
	if err != nil {
		return nil, fmt.Errorf("redirect: %w", err)
	}
	var buf bytes.Buffer
	err = c.api.Do(ctx, "GET", location, httpclient.WithResponseUnmarshal(&buf))
	return &buf, err
}

func (c *GitHubClient) ListRuns(ctx context.Context, org, repo, workflow string) listing.Iterator[workflowRun] {
	path := fmt.Sprintf("%s/repos/%s/%s/actions/workflows/%v.yml/runs", gitHubAPI, org, repo, workflow)
	type response struct {
		WorkflowRuns []workflowRun `json:"workflow_runs,omitempty"`
	}
	return rawPaginator[workflowRun, response, int64](ctx, c, path, &PageOptions{}, func(r response) []workflowRun {
		return r.WorkflowRuns
	}, func(wr workflowRun) int64 {
		return wr.ID
	})
}

func (c *GitHubClient) ListWorkflowJobs(ctx context.Context, org, repo string, runID int64) listing.Iterator[WorkflowJob] {
	path := fmt.Sprintf("%s/repos/%s/%s/actions/runs/%v/jobs", gitHubAPI, org, repo, runID)
	return rawPaginator[WorkflowJob, Jobs, int64](ctx, c, path, &PageOptions{}, func(j Jobs) []WorkflowJob {
		return j.Jobs
	}, func(wj WorkflowJob) int64 {
		return wj.ID
	})
}

func (c *GitHubClient) ListCommits(ctx context.Context, org, repo string, req *ListCommits) listing.Iterator[RepositoryCommit] {
	path := fmt.Sprintf("%s/repos/%s/%s/commits", gitHubAPI, org, repo)
	return paginator[RepositoryCommit, string](ctx, c, path, req, func(rc RepositoryCommit) string {
		return rc.SHA
	})
}

func (c *GitHubClient) GetCommit(ctx context.Context, org, repo string, sha string) (*RepositoryCommit, error) {
	var res RepositoryCommit
	path := fmt.Sprintf("%s/repos/%s/%s/commits/%s", gitHubAPI, org, repo, sha)
	err := c.api.Do(ctx, "GET", path, httpclient.WithResponseUnmarshal(&res))
	return &res, err
}

func (c *GitHubClient) CompareCommits(ctx context.Context, org, repo, base, head string) listing.Iterator[RepositoryCommit] {
	type response struct {
		Commits []RepositoryCommit `json:"commits,omitempty"`
	}
	path := fmt.Sprintf("%s/repos/%v/%v/compare/%v...%v", gitHubAPI, org, repo, base, head)
	return rawPaginator[RepositoryCommit, response, string](ctx, c, path, &PageOptions{}, func(r response) []RepositoryCommit {
		return r.Commits
	}, func(rc RepositoryCommit) string {
		return rc.SHA
	})
}

func (c *GitHubClient) ListPullRequests(ctx context.Context, org, repo string, opts *ListPullRequests) listing.Iterator[PullRequest] {
	path := fmt.Sprintf("%s/repos/%s/%s/pulls", gitHubAPI, org, repo)
	return paginator[PullRequest, int64](ctx, c, path, opts, func(pr PullRequest) int64 {
		return pr.ID
	})
}

func (c *GitHubClient) EditPullRequest(ctx context.Context, org, repo string, number int, body UpdatePullRequest) error {
	path := fmt.Sprintf("%s/repos/%s/%s/pulls/%d", gitHubAPI, org, repo, number)
	return c.api.Do(ctx, "PATCH", path, httpclient.WithRequestData(body))
}

func (c *GitHubClient) CreatePullRequest(ctx context.Context, org, repo string, body NewPullRequest) (*PullRequest, error) {
	path := fmt.Sprintf("%s/repos/%s/%s/pulls", gitHubAPI, org, repo)
	var res PullRequest
	err := c.api.Do(ctx, "POST", path,
		httpclient.WithRequestData(body),
		httpclient.WithResponseUnmarshal(&res))
	if err != nil {
		return nil, err
	}
	return &res, nil
}

func (c *GitHubClient) GetPullRequest(ctx context.Context, org, repo string, number int) (*PullRequest, error) {
	path := fmt.Sprintf("%s/repos/%s/%s/pulls/%d", gitHubAPI, org, repo, number)
	var res PullRequest
	err := c.api.Do(ctx, "GET", path,
		httpclient.WithResponseUnmarshal(&res))
	return &res, err
}

func (c *GitHubClient) GetPullRequestComments(ctx context.Context, org, repo string, number int) listing.Iterator[PullRequestComment] {
	path := fmt.Sprintf("%s/repos/%s/%s/pulls/%d/comments", gitHubAPI, org, repo, number)
	return paginator[PullRequestComment, int64](ctx, c, path, &PageOptions{}, func(prc PullRequestComment) int64 {
		return prc.ID
	})
}

func (c *GitHubClient) GetPullRequestReviews(ctx context.Context, org, repo string, number int) listing.Iterator[PullRequestReview] {
	path := fmt.Sprintf("%s/repos/%s/%s/pulls/%d/reviews", gitHubAPI, org, repo, number)
	return paginator[PullRequestReview, int64](ctx, c, path, &PageOptions{}, func(prr PullRequestReview) int64 {
		return prr.ID
	})
}

func (c *GitHubClient) GetPullRequestCommits(ctx context.Context, org, repo string, number int) listing.Iterator[RepositoryCommit] {
	path := fmt.Sprintf("%s/repos/%s/%s/pulls/%d/commits", gitHubAPI, org, repo, number)
	return paginator[RepositoryCommit, string](ctx, c, path, &PageOptions{}, func(rc RepositoryCommit) string {
		return rc.SHA
	})
}

// GetIssueComments returns comments for a number, which can be issue # or pr #
// Every pull request is an issue, but not every issue is a pull request.
func (c *GitHubClient) GetIssueComments(ctx context.Context, org, repo string, number int) listing.Iterator[IssueComment] {
	path := fmt.Sprintf("%s/repos/%s/%s/issues/%d/comments", gitHubAPI, org, repo, number)
	return paginator[IssueComment, int64](ctx, c, path, &PageOptions{}, func(ic IssueComment) int64 {
		return ic.ID
	})
}

func (c *GitHubClient) CreateIssueComment(ctx context.Context, org, repo string, number int, body string) (*IssueComment, error) {
	path := fmt.Sprintf("%s/repos/%s/%s/issues/%d/comments", gitHubAPI, org, repo, number)
	var res IssueComment
	err := c.api.Do(ctx, "POST", path,
		httpclient.WithRequestData(map[string]string{
			"body": body,
		}),
		httpclient.WithResponseUnmarshal(&res))
	if err != nil {
		return nil, err
	}
	return &res, nil
}

func (c *GitHubClient) UpdateIssueComment(ctx context.Context, org, repo string, commentID int64, body string) (*IssueComment, error) {
	path := fmt.Sprintf("%s/repos/%s/%s/issues/comments/%d", gitHubAPI, org, repo, commentID)
	var res IssueComment
	err := c.api.Do(ctx, "PATCH", path,
		httpclient.WithRequestData(map[string]string{
			"body": body,
		}),
		httpclient.WithResponseUnmarshal(&res))
	if err != nil {
		return nil, err
	}
	return &res, nil
}

func (c *GitHubClient) DeleteIssueComment(ctx context.Context, org, repo string, commentID int64) error {
	path := fmt.Sprintf("%s/repos/%s/%s/issues/comments/%d", gitHubAPI, org, repo, commentID)
	return c.api.Do(ctx, "DELETE", path)
}

func (c *GitHubClient) GetRepoTrafficClones(ctx context.Context, org, repo string) ([]ClonesStat, error) {
	path := fmt.Sprintf("%s/repos/%s/%s/traffic/clones", gitHubAPI, org, repo)
	var res struct {
		Clones []ClonesStat `json:"clones"`
	}
	err := c.api.Do(ctx, "GET", path,
		httpclient.WithResponseUnmarshal(&res))
	return res.Clones, err
}

func (c *GitHubClient) GetRepoTrafficViews(ctx context.Context, org, repo string) ([]ViewsStat, error) {
	path := fmt.Sprintf("%s/repos/%s/%s/traffic/views", gitHubAPI, org, repo)
	var res struct {
		Views []ViewsStat `json:"views"`
	}
	err := c.api.Do(ctx, "GET", path,
		httpclient.WithResponseUnmarshal(&res))
	return res.Views, err
}

func (c *GitHubClient) GetRepoTrafficPaths(ctx context.Context, org, repo string) (res []PopularPathStat, err error) {
	path := fmt.Sprintf("%s/repos/%s/%s/traffic/popular/paths", gitHubAPI, org, repo)
	err = c.api.Do(ctx, "GET", path,
		httpclient.WithResponseUnmarshal(&res))
	return res, err
}

func (c *GitHubClient) GetRepoTrafficReferrals(ctx context.Context, org, repo string) (res []ReferralSourceStat, err error) {
	path := fmt.Sprintf("%s/repos/%s/%s/traffic/popular/referrers", gitHubAPI, org, repo)
	err = c.api.Do(ctx, "GET", path,
		httpclient.WithResponseUnmarshal(&res))
	return res, err
}

func (c *GitHubClient) GetRepoStargazers(ctx context.Context, org, repo string) listing.Iterator[Stargazer] {
	path := fmt.Sprintf("%s/repos/%s/%s/stargazers", gitHubAPI, org, repo)
	return paginator[Stargazer, string](ctx, c, path, &ListStargazers{}, func(s Stargazer) string {
		return s.User.Login
	})
}

func (c *GitHubClient) GetUser(ctx context.Context, login string) (*User, error) {
	path := fmt.Sprintf("%s/users/%s", gitHubAPI, login)
	var user User
	err := c.api.Do(ctx, "GET", path,
		httpclient.WithResponseUnmarshal(&user))
	return &user, err
}

func (c *GitHubClient) CurrentUser(ctx context.Context) (*User, error) {
	path := fmt.Sprintf("%s/user", gitHubAPI)
	var user User
	err := c.api.Do(ctx, "GET", path,
		httpclient.WithResponseUnmarshal(&user))
	return &user, err
}

func (c *GitHubClient) ListTeams(ctx context.Context, org string) listing.Iterator[Team] {
	path := fmt.Sprintf("%s/orgs/%s/teams", gitHubAPI, org)
	return paginator[Team, string](ctx, c, path, &PageOptions{}, func(t Team) string {
		return t.Slug
	})
}

func (c *GitHubClient) CreateTeam(ctx context.Context, org string, req NewTeam) (*Team, error) {
	var res Team
	path := fmt.Sprintf("%s/orgs/%s/teams", gitHubAPI, org)
	err := c.api.Do(ctx, "POST", path,
		httpclient.WithRequestData(req),
		httpclient.WithResponseUnmarshal(&res))
	return &res, err
}

func (c *GitHubClient) DeleteTeam(ctx context.Context, org, slug string) error {
	path := fmt.Sprintf("%s/orgs/%s/teams/%s", gitHubAPI, org, slug)
	return c.api.Do(ctx, "DELETE", path)
}

func (c *GitHubClient) ListTeamMembers(ctx context.Context, org, slug string) listing.Iterator[User] {
	path := fmt.Sprintf("%s/orgs/%s/teams/%s/members", gitHubAPI, org, slug)
	return paginator[User, string](ctx, c, path, &PageOptions{}, func(u User) string {
		return u.Login
	})
}

func (c *GitHubClient) AddTeamMember(ctx context.Context, org, teamSlug, username string) error {
	path := fmt.Sprintf("%s/orgs/%s/teams/%s/members/%s", gitHubAPI, org, teamSlug, username)
	return c.api.Do(ctx, "POST", path)
}

func (c *GitHubClient) RemoveTeamMember(ctx context.Context, org, teamSlug, username string) error {
	path := fmt.Sprintf("%s/orgs/%s/teams/%s/members/%s", gitHubAPI, org, teamSlug, username)
	return c.api.Do(ctx, "DELETE", path)
}

func (c *GitHubClient) GraphQL(ctx context.Context, query string, vars map[string]any, data any) error {
	return c.api.Do(ctx, "POST", "https://api.github.com/graphql",
		httpclient.WithRequestData(map[string]any{
			"query":     query,
			"variables": vars,
		}),
		httpclient.WithResponseUnmarshal(data))
}

func paginator[T any, ID comparable](
	ctx context.Context,
	c *GitHubClient,
	path string,
	request iteratableRequest,
	getId func(T) ID,
) listing.Iterator[T] {
	return rawPaginator[T, []T, ID](ctx, c, path, request, func(res []T) []T {
		return res
	}, getId)
}

type visitingRequest interface {
	visitRequest(r *http.Request) error
}

func rawPaginator[T any, R any, ID comparable](
	ctx context.Context,
	c *GitHubClient,
	path string,
	request iteratableRequest,
	getItems func(R) []T,
	getId func(T) ID,
) listing.Iterator[T] {
	request.defaults()
	return listing.NewDedupeIterator(listing.NewIterator(&request,
		func(ctx context.Context, po iteratableRequest) (R, error) {
			var res R
			err := c.api.Do(ctx, "GET", path,
				httpclient.WithRequestVisitor(func(r *http.Request) error {
					if vr, ok := po.(visitingRequest); ok {
						// sometimes we need to add headers
						err := vr.visitRequest(r)
						if err != nil {
							return err
						}
					}
					qs, err := query.Values(request)
					if err != nil {
						return err
					}
					r.URL.RawQuery = qs.Encode()
					return nil
				}),
				httpclient.WithResponseUnmarshal(&res))
			if len(getItems(res)) == 0 {
				return res, listing.ErrNoMoreItems
			}
			return res, err
		}, getItems, func(_ R) *iteratableRequest {
			request.increment()
			return &request
		}), getId)
}
