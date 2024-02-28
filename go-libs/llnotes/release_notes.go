package llnotes

import (
	"context"
	"fmt"
	"strings"

	"github.com/databricks/databricks-sdk-go/listing"
)

const blogPrompt = `SYSTEM:
You are professional technical writer and you receive draft release notes for %s of project called %s in a markdown format from multiple team members. 
Project can be described as "%s"

You write a long post announcement that takes 5 minutes to read, summarize the most important features, and mention them on top. Keep the markdown links when relevant.
Do not use headings. Write fluent paragraphs, that are at least few sentences long. Blog post title should nicely summarize the feature increments of this release.

Don't abuse lists. paragraphs should have at least 3-4 sentences. The title should be one-sentence summary of the incremental updates for this release

You aim at driving more adoption of the project on Medium.

USER:
`

func (lln *llNotes) ReleaseNotes(ctx context.Context) (History, error) {
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
	commits, err := listing.ToSlice(ctx,
		lln.gh.CompareCommits(ctx, lln.org, lln.repo, latestTag, repo.DefaultBranch))
	if err != nil {
		return nil, fmt.Errorf("compare commits: %w", err)
	}
	rawNotes := []string{}
	for _, c := range commits {
		rawNotes = append(rawNotes, c.Commit.Message)
	}
	return lln.Talk(ctx, History{
		SystemMessage(fmt.Sprintf(blogPrompt, latestTag, repo.Name, repo.Description)),
		UserMessage(strings.Join(rawNotes, "\n")),
	})
}
