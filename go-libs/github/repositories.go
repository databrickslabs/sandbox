package github

import (
	"context"
	"fmt"
	"time"

	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/localcache"
)

const repositoryCacheTTL = 24 * time.Hour

func NewRepositoryCache(client *GitHubClient, org, cacheDir string) *repositoryCache {
	filename := fmt.Sprintf("%s-repositories", org)
	return &repositoryCache{
		cache:  localcache.NewLocalCache[Repositories](cacheDir, filename, repositoryCacheTTL),
		client: client,
		Org:    org,
	}
}

type repositoryCache struct {
	cache  localcache.LocalCache[Repositories]
	client *GitHubClient
	Org    string
}

func (r *repositoryCache) Load(ctx context.Context) (Repositories, error) {
	return r.cache.Load(ctx, func() (Repositories, error) {
		logger.Debugf(ctx, "Loading repositories for %s from GitHub API", r.Org)
		return listing.ToSlice[Repo](ctx, r.client.ListRepositories(ctx, r.Org))
	})
}

type Repositories []Repo

type Repo struct {
	Name          string    `json:"name"`
	Owner         User      `json:"user"`
	Description   string    `json:"description"`
	Langauge      string    `json:"language"`
	DefaultBranch string    `json:"default_branch"`
	Stars         int       `json:"stargazers_count"`
	IsFork        bool      `json:"fork"`
	IsPrivate     bool      `json:"private"`
	IsArchived    bool      `json:"archived"`
	Topics        []string  `json:"topics"`
	HtmlURL       string    `json:"html_url"`
	CloneURL      string    `json:"clone_url"`
	SshURL        string    `json:"ssh_url"`
	Visibility    string    `json:"visibility"`
	UpdatedAt     time.Time `json:"updated_at"`
	PushedAt      time.Time `json:"pushed_at"`

	License struct {
		Name string `json:"name"`
	} `json:"license"`
}
