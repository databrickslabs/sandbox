package git

import (
	"context"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/databrickslabs/sandbox/go-libs/counters"
)

// See https://git-scm.com/docs/pretty-formats for docs

// See https://git-scm.com/docs/git-log
// shows number of added and deleted lines in decimal notation and pathname without abbreviation,
// to make it more machine friendly. For binary files, outputs two - instead of saying 0 0.
type NumStat struct {
	Added    int    `json:"added"`
	Deleted  int    `json:"deleted"`
	Pathname string `json:"pathname"`
}

type CommitInfo struct {
	// %aI - author date, strict ISO 8601 format
	Time time.Time `json:"time"`

	// %H - commit hash
	Sha string `json:"sha"`

	// %aN - author name (respecting .mailmap, see git-shortlog[1] or git-blame[1])
	Author string `json:"author"`

	// %aE - author email (respecting .mailmap, see git-shortlog[1] or git-blame[1])
	Email string `json:"email"`

	Stats []NumStat `json:"stats"`
}

func (l *Checkout) History(ctx context.Context) (Commits, error) {
	raw, err := l.cmd(ctx, "log", "--all", "--pretty=commit,%at,%H,%aN,%aE", "--numstat")
	if err != nil {
		return nil, err
	}
	var out Commits
	var current CommitInfo
	lines := strings.Split(raw, "\n")
	for _, l := range lines {
		if strings.HasPrefix(l, "commit") {
			// New commit found, save the previous commit (if any)
			if current.Sha != "" {
				out = append(out, current)
			}
			fields := strings.Split(l, ",")
			current = CommitInfo{
				Time:   time.Unix(int64(parseStat(fields[1])), 0),
				Sha:    fields[2],
				Author: fields[3],
				Email:  fields[4],
			}
			continue
		}
		if strings.Contains(l, "\t") {
			fields := strings.Fields(l)
			if len(fields) < 3 {
				continue
			}
			current.Stats = append(current.Stats, NumStat{
				Added:    parseStat(fields[0]),
				Deleted:  parseStat(fields[1]),
				Pathname: fields[2],
			})
		}
	}
	if current.Sha != "" {
		out = append(out, current)
	}
	return out, nil
}

func parseStat(stat string) int {
	num, err := strconv.Atoi(stat)
	if err != nil {
		return 0
	}
	return num
}

type Commits []CommitInfo

type AuthorInfo struct {
	Author  string `json:"author"`
	Email   string `json:"email"`
	Commits int    `json:"commits"`
	Added   int    `json:"added"`
	Deleted int    `json:"deleted"`
}

func (a AuthorInfo) Totals() int {
	return a.Commits + a.Added + a.Deleted
}

func (all Commits) Started() time.Time {
	started := time.Now()
	for _, v := range all {
		if v.Time.Before(started) {
			started = v.Time
		}
	}
	return started
}

func (all Commits) Ended() time.Time {
	started := time.Time{}
	for _, v := range all {
		if v.Time.After(started) {
			started = v.Time
		}
	}
	return started
}

// Filter reduces the history based on the predicate from path
func (all Commits) Filter(predicate func(pathname string) bool) (out Commits) {
	for _, c := range all {
		stats := []NumStat{}
		for _, ns := range c.Stats {
			// we don't handle path renames
			if !predicate(ns.Pathname) {
				continue
			}
			stats = append(stats, ns)
		}
		if len(stats) == 0 {
			continue
		}
		out = append(out, CommitInfo{
			Time:   c.Time,
			Sha:    c.Sha,
			Author: c.Author,
			Email:  c.Email,
			Stats:  stats,
		})
	}
	return out
}

func (all Commits) LanguageStats() counters.Counter[string] {
	// this is a straightforward code language detection strategy
	stats := counters.NewStringCounter()
	for _, c := range all {
		for _, ns := range c.Stats {
			split := strings.Split(ns.Pathname, ".")
			ext := split[len(split)-1]
			stats.AddN(ext, ns.Added+ns.Deleted)
		}
		if len(stats) == 0 {
			continue
		}
	}
	return stats
}

func (all Commits) Language() string {
	return all.LanguageStats().HeadOrDefault("unknown")
}

func (all Commits) Authors() (out Authors) {
	type tmp struct {
		Author, Email string
	}
	commits := counters.Counter[tmp]{}
	added := counters.Counter[tmp]{}
	deleted := counters.Counter[tmp]{}
	// other interesting metrics: unique hours worked based on hour-truncated git commit timestamps
	for _, c := range all {
		k := tmp{c.Author, c.Email}
		commits.Add(k)
		for _, s := range c.Stats {
			added.AddN(k, s.Added)
			deleted.AddN(k, s.Deleted)
		}
	}
	for k, commits := range commits {
		out = append(out, AuthorInfo{
			Author:  k.Author,
			Email:   k.Email,
			Commits: commits,
			Added:   added[k],
			Deleted: deleted[k],
		})
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].Totals() > out[j].Totals()
	})
	return out
}

type Authors []AuthorInfo

func (authors Authors) Primary() string {
	top := authors.Top(1)
	if len(top) == 0 {
		panic("no authors?...")
	}
	return top[0]
}

func (authors Authors) Top(atMost int) []string {
	if atMost > len(authors) {
		atMost = len(authors)
	}
	var out []string
	for _, v := range authors {
		if v.Email == "action@github.com" {
			continue
		}
		if v.Author == "dependabot[bot]" {
			continue
		}
		out = append(out, v.Author)
	}
	return out[:atMost]
}
