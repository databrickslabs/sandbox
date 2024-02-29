package llnotes

import (
	"bytes"
	"context"
	"fmt"

	"github.com/databricks/databricks-sdk-go/httpclient"
	"github.com/databrickslabs/sandbox/go-libs/github"
)

var fileDiffTemplate = MessageTemplate(`Here is the commit message terminated by --- for the context:
{{.Message}}
---

Do not hallucinate. 
You are Staff Software Engineer, and you are reviewing one file at a time in a unitified diff format. 
Do not use phrases like "In this diff", "In this pull request", or "In this file". 
Do not mention file names, because they are not relevant for the feature description.
If new methods are added, explain what these methods are doing. 
If existing funcitonality is changed, explain the scope of these changes.
Please summarize the input as a signle paragraph of text written in American English. 
Your target audience is software engineers, who adopt your project.
If the prompt contains ordered or unordered lists, rewrite the entire response as a paragraph of text.`)

func (lln *llNotes) CommitBySHA(ctx context.Context, sha string) (History, error) {
	commit, err := lln.gh.GetCommit(ctx, lln.org, lln.repo, sha)
	if err != nil {
		return nil, fmt.Errorf("commit: %w", err)
	}
	return lln.Commit(ctx, commit)
}

func (lln *llNotes) Commit(ctx context.Context, commit *github.RepositoryCommit) (History, error) {
	var buf bytes.Buffer
	err := lln.http.Do(ctx, "GET",
		fmt.Sprintf("https://github.com/%s/%s/commit/%s.diff", lln.org, lln.repo, commit.SHA),
		httpclient.WithResponseUnmarshal(&buf))
	if err != nil {
		return nil, fmt.Errorf("fetch diff: %w", err)
	}
	return lln.explainDiff(ctx, History{
		fileDiffTemplate.AsSystem(commit.Commit),
	}, &buf)
}

func (lln *llNotes) PullRequest(ctx context.Context, number int) (History, error) {
	pr, err := lln.gh.GetPullRequest(ctx, lln.org, lln.repo, number)
	if err != nil {
		return nil, fmt.Errorf("pull request: %w", err)
	}
	var buf bytes.Buffer
	err = lln.http.Do(ctx, "GET", pr.DiffURL, httpclient.WithResponseUnmarshal(&buf))
	if err != nil {
		return nil, fmt.Errorf("fetch diff: %w", err)
	}
	return lln.explainDiff(ctx, History{
		fileDiffTemplate.AsSystem(map[string]string{
			"Message": pr.Title,
		}),
	}, &buf)
}
