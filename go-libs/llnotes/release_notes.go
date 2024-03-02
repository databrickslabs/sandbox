package llnotes

import (
	"context"
	"fmt"
	"strings"

	"github.com/databricks/databricks-sdk-go/listing"
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

func (lln *llNotes) ReleaseNotesDiff(ctx context.Context, since, until string) ([]string, error) {
	commits, err := listing.ToSlice(ctx, lln.gh.CompareCommits(ctx, lln.org, lln.repo, since, until))
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
	return parallel.Tasks(ctx, lln.cfg.Workers, commits,
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
}
