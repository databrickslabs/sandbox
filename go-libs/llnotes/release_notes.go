package llnotes

import (
	"context"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/databrickslabs/sandbox/go-libs/parallel"
	"github.com/databrickslabs/sandbox/go-libs/sed"
)

func (lln *llNotes) UpcomingRelease(ctx context.Context) ([]string, error) {
	versions, err := listing.ToSlice(ctx, lln.gh.Versions(ctx, lln.org, lln.repo))
	if err != nil {
		return nil, fmt.Errorf("versions: %w", err)
	}
	repo, err := lln.gh.GetRepo(ctx, lln.org, lln.repo)
	if err != nil {
		return nil, fmt.Errorf("get repo: %w", err)
	}
	latestTag := "v0.0.0" // special value for first-release projects
	if len(versions) > 0 {
		latestTag = versions[0].Version
	}
	return lln.ReleaseNotesDiff(ctx, latestTag, repo.DefaultBranch)
}

var maybePrRE = regexp.MustCompile(`\(#(\d+)\)$`)

func (lln *llNotes) filterOutCommitsWithSkipLabels(ctx context.Context, in []github.RepositoryCommit) ([]github.RepositoryCommit, error) {
	if len(lln.cfg.SkipLabels) == 0 {
		logger.Debugf(ctx, "No skip labels configured. Keeping all commits.")
		return in, nil
	}
	var out []github.RepositoryCommit
iterateCommits:
	for _, commit := range in {
		for _, skip := range lln.cfg.SkipCommits {
			if commit.SHA == skip {
				logger.Infof(ctx, "Skipping commit %s: %s", commit.SHA, commit.Commit.Message)
				continue iterateCommits
			}
		}
		if commit.Commit.Message == "" {
			continue
		}
		title, _, ok := strings.Cut(commit.Commit.Message, "\n")
		if !ok {
			title = commit.Commit.Message
		}
		match := maybePrRE.FindStringSubmatch(title)
		if len(match) == 0 {
			logger.Debugf(ctx, "Keeping commit %s: no PR reference", commit.SHA)
			out = append(out, commit)
			continue
		}
		number, err := strconv.Atoi(match[1])
		if err != nil {
			return nil, fmt.Errorf("invalid PR number: %w", err)
		}
		pr, err := lln.gh.GetPullRequest(ctx, lln.org, lln.repo, number)
		if err != nil {
			return nil, fmt.Errorf("get PR: %w", err)
		}
		for _, label := range pr.Labels {
			for _, skip := range lln.cfg.SkipLabels {
				if label.Name == skip {
					logger.Infof(ctx, "Skipping '%s': %s", title, skip)
					continue iterateCommits
				}
			}
		}
		out = append(out, commit)
	}
	return out, nil
}

func (lln *llNotes) ReleaseNotesDiff(ctx context.Context, since, until string) ([]string, error) {
	raw, err := listing.ToSlice(ctx, lln.gh.CompareCommits(ctx, lln.org, lln.repo, since, until))
	if err != nil {
		return nil, fmt.Errorf("commits: %w", err)
	}
	var cleanup = sed.Pipeline{
		sed.Rule("^Add ", "Added "),
		sed.Rule("^Adding ", "Added "),
		sed.Rule("^Apply ", "Applied "),
		sed.Rule("^Change ", "Changed "),
		sed.Rule("^Enable ", "Enabled "),
		sed.Rule("^Handle ", "Added handling for "),
		sed.Rule("^Enforce ", "Enforced "),
		sed.Rule("^Migrate ", "Added migration for "),
		sed.Rule("^Fix ", "Fixed "),
		sed.Rule("^Move ", "Moved "),
		sed.Rule("^Update ", "Updated "),
		sed.Rule("^Remove ", "Removed "),
		sed.Rule(` '([\w\s_-]+)' `, " `$1` "),
		sed.Rule(` "([\w\s_-]+)" `, " `$1` "),
		sed.Rule(`#(\d+)`, fmt.Sprintf("[#$1](https://github.com/%s/%s/issues/$1)", lln.org, lln.repo)),
		sed.Rule(`\. \(`, ` (`),
	}
	commits, err := lln.filterOutCommitsWithSkipLabels(ctx, raw)
	if err != nil {
		return nil, fmt.Errorf("filter: %w", err)
	}
	notes, err := parallel.Tasks(ctx, lln.cfg.Workers, commits,
		func(ctx context.Context, commit github.RepositoryCommit) (string, error) {
			history, err := lln.Commit(ctx, &commit)
			if err != nil {
				return "", fmt.Errorf("commit: %s: %w", commit.SHA, err)
			}
			short := strings.Split(commit.Commit.Message, "\n")[0]
			line := fmt.Sprintf("%s. %s", short, history.Last())
			line = lln.norm.Apply(line)
			line = cleanup.Apply(line)
			return line, nil
		})
	if err != nil {
		return nil, fmt.Errorf("parallel: %w", err)
	}
	sort.Strings(notes)
	return notes, nil
}
