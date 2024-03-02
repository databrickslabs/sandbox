package llnotes

import (
	"context"
	"fmt"
	"strings"

	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/databricks/databricks-sdk-go/logger"
)

var blogPrompt = MessageTemplate(`Do not hallucinate.
You are professional technical writer and you receive draft release notes for {{.version}} of project called {{.repo.Name}} in a markdown format from multiple team members. 
Project can be described as "{{.repo.Description}}"

You write a long post announcement that takes at least 5 minutes to read, summarize the most important features, and mention them on top. Keep the markdown links when relevant.
Do not use headings. Write fluent paragraphs, that are at least few sentences long. Blog post title should nicely summarize the feature increments of this release.

Don't abuse lists. paragraphs should have at least 3-4 sentences. The title should be one-sentence summary of the incremental updates for this release

You aim at driving more adoption of the project on Medium.`)

func (lln *llNotes) versionNotes(ctx context.Context, newVersion string) ([]string, error) {
	versions, err := listing.ToSlice(ctx, lln.gh.Versions(ctx, lln.org, lln.repo))
	if err != nil {
		return nil, fmt.Errorf("versions: %w", err)
	}
	if newVersion == "" {
		newVersion = versions[0].Version
	}
	prevVersion := "v0.0.0"
	for i, v := range versions {
		if v.Version == newVersion {
			prevVersion = versions[i+1].Version
			break
		}
	}
	return lln.ReleaseNotesDiff(ctx, prevVersion, newVersion)
}

func (lln *llNotes) Announce(ctx context.Context, newVersion string) (History, error) {
	notes, err := lln.versionNotes(ctx, newVersion)
	if err != nil {
		return nil, fmt.Errorf("parallel: %w", err)
	}
	repo, err := lln.gh.GetRepo(ctx, lln.org, lln.repo)
	if err != nil {
		return nil, fmt.Errorf("get repo: %w", err)
	}
	rawNotes := strings.Join(notes, "\n")
	logger.Debugf(ctx, "Raw notes: %s", rawNotes)
	return lln.Talk(ctx, History{
		blogPrompt.AsSystem(map[string]any{
			"version": newVersion,
			"repo":    repo,
		}),
		UserMessage(rawNotes),
	})
}
