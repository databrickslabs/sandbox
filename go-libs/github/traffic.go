package github

import (
	"net/http"
	"time"
)

type ClonesStat struct {
	Timestamp time.Time `json:"timestamp,omitempty"`
	Count     int       `json:"count"`
	Uniques   int       `json:"uniques"`
}

type ViewsStat struct {
	Timestamp time.Time `json:"timestamp,omitempty"`
	Count     int       `json:"count"`
	Uniques   int       `json:"uniques"`
}

type PopularPathStat struct {
	Path    string `json:"path"`
	Title   string `json:"title"`
	Count   int    `json:"count"`
	Uniques int    `json:"uniques"`
}

type ReferralSourceStat struct {
	Referrer string `json:"referrer"`
	Count    int    `json:"count"`
	Uniques  int    `json:"uniques"`
}

type ListStargazers struct {
	PageOptions
}

func (*ListStargazers) visitRequest(r *http.Request) error {
	r.Header.Add("Accept", "application/vnd.github.v3.star+json")
	return nil
}

type Stargazer struct {
	StarredAt time.Time `json:"starred_at"`
	User      User      `json:"user"`
}
