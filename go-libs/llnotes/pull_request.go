package llnotes

import (
	"bytes"
	"context"

	"github.com/databricks/databricks-sdk-go/httpclient"
)

const prPrompt = `You are a staff software engineer, and you are reviewing code in a pull request. If new methods are added, explain what these methods are doing. 
If this pull request has changes to tests, give a summary of scenarios that are tested. Please summarize this pull request in one paragraph. 
Changes related to tests should be in a separate paragraph.`

func (lln *llNotes) PullRequest(ctx context.Context, number int) (History, error) {
	pr, err := lln.gh.GetPullRequest(ctx, lln.org, lln.repo, number)
	if err != nil {
		return nil, err
	}
	var buf bytes.Buffer
	err = lln.http.Do(ctx, "GET", pr.DiffURL, httpclient.WithResponseUnmarshal(&buf))
	if err != nil {
		return nil, err
	}
	return lln.Talk(ctx, History{
		SystemMessage(prPrompt),
		UserMessage(buf.String()),
	})
}
