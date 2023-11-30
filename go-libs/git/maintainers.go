package git

import (
	"context"
	"sort"
	"strconv"
	"strings"
	"time"
)

// See https://git-scm.com/docs/pretty-formats for docs

// See https://git-scm.com/docs/git-log
// shows number of added and deleted lines in decimal notation and pathname without abbreviation,
// to make it more machine friendly. For binary files, outputs two - instead of saying 0 0.
type NumStat struct {
	Added    int
	Deleted  int
	Pathname string
}

type CommitInfo struct {
	// %aI - author date, strict ISO 8601 format
	Time time.Time

	// %H - commit hash
	Sha string

	// %aN - author name (respecting .mailmap, see git-shortlog[1] or git-blame[1])
	Author string

	// %aE - author email (respecting .mailmap, see git-shortlog[1] or git-blame[1])
	Email string

	Stats []NumStat
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
	Author  string
	Email   string
	Commits int
	Added   int
	Deleted int
}

func (a AuthorInfo) Totals() int {
	return a.Commits + a.Added + a.Deleted
}

func (all Commits) ContributorsRaw() (out Authors) {
	// this method doesn't count contributions per folder
	type tmp struct {
		Author, Email string
	}
	commits := map[tmp]int{}
	added := map[tmp]int{}
	deleted := map[tmp]int{}
	// other interesting metrics: unique hours worked based on hour-truncated git commit timestamps
	for _, c := range all {
		k := tmp{c.Author, c.Email}
		commits[k] += 1
		for _, s := range c.Stats {
			added[k] += s.Added
			deleted[k] += s.Deleted
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
