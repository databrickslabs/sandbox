package github

import (
	"context"
	"fmt"
	"time"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/localcache"
)

const cacheTTL = 1 * time.Hour

// NewReleaseCache creates a release cache for a repository in the GitHub org.
// Caller has to provide different cache directories for different repositories.
func NewReleaseCache(org, repo, cacheDir string) *ReleaseCache {
	pattern := fmt.Sprintf("%s-%s-releases", org, repo)
	return &ReleaseCache{
		cache: localcache.NewLocalCache[Versions](cacheDir, pattern, cacheTTL),
		Org:   org,
		Repo:  repo,
	}
}

type ReleaseCache struct {
	cache localcache.LocalCache[Versions]
	Org   string
	Repo  string
}

func (r *ReleaseCache) Load(ctx context.Context) (Versions, error) {
	return r.cache.Load(ctx, func() (Versions, error) {
		return getVersions(ctx, r.Org, r.Repo)
	})
}

// getVersions is considered to be a private API, as we want the usage go through a cache
func getVersions(ctx context.Context, org, repo string) (Versions, error) {
	var releases Versions
	logger.Debugf(ctx, "Fetching latest releases for %s/%s from GitHub API", org, repo)
	url := fmt.Sprintf("%s/repos/%s/%s/releases", gitHubAPI, org, repo)
	err := httpGetAndUnmarshal(ctx, url, &releases)
	return releases, err
}

type ghAsset struct {
	Name               string `json:"name"`
	ContentType        string `json:"content_type"`
	Size               int    `json:"size"`
	BrowserDownloadURL string `json:"browser_download_url"`
}

type Release struct {
	Version     string    `json:"tag_name"`
	CreatedAt   time.Time `json:"created_at"`
	PublishedAt time.Time `json:"published_at"`
	ZipballURL  string    `json:"zipball_url"`
	Assets      []ghAsset `json:"assets"`
}

type Versions []Release
