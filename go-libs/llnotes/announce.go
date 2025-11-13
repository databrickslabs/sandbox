package llnotes

import (
	"context"
	"fmt"
	"strings"

	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/databricks/databricks-sdk-go/logger"
)

var blogPrompt = MessageTemplate(`Role: Technical content writer for {{.repo.Name}} release announcements.

Project: {{.repo.Description}}
Version: {{.version}}

Task: Create a concise blog post announcing this release.

Structure:
1. Title: One-sentence summary of key improvements (10-15 words)
2. Opening: Lead with the most impactful feature (2-3 sentences)
3. Key Changes: 3-5 paragraphs, each covering one major feature area
4. Summary: Brief closing with call-to-action (1-2 sentences)

Requirements:
- Target length: 400-600 words (3-4 minute read)
- Each paragraph: 3-5 sentences focused on user benefits
- Use bullet points sparingly (max 1 list if essential)
- Maintain technical accuracy while being accessible
- Include markdown links from original notes
- Emphasize adoption value and practical use cases

Tone: Professional, enthusiastic, developer-focused`)

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
