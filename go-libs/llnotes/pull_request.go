package llnotes

import (
	"bytes"
	"context"
	"fmt"
	"regexp"
	"strings"

	"github.com/databricks/databricks-sdk-go/httpclient"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/sourcegraph/go-diff/diff"
)

const fileDiffPrompt = `Do not hallucinate. 
You are Staff Software Engineer, and you are reviewing one file at a time in a unitified diff format. 
Do not use phrases like "In this diff" or "In this pull request".
If new methods are added, explain what these methods are doing. 
If existing funcitonality is changed, explain the scope of these changes.
Please summarize the input as a signle paragraph of text written in American English. 
Your target audience is software engineers, who adopt your project.
If the prompt contains ordered or unordered lists, rewrite the entire response as a paragraph of text.`

const reduceDiffPrompt = `Do not hallucinate. 
You are a professional Technical Writer writing feature change description for the open-source library.
Do not use phrases like "In this release".
Your target audience is software engineers. 
You receive a change description from your software engineering team about the newly developed features. 
Write a one-paragraph summary of this change for the release notes. 
It has to be one paragraph of text, because it will be included in a bigger document.`

var repeatedWhitespace = regexp.MustCompile(`\s+`)
var orderedListAbuse = regexp.MustCompile(`\n([0-9]+)\. `)
var unorderedListAbuse = regexp.MustCompile(`\n\s?- `)

func (lln *llNotes) normalizedResponse(response string) string {
	// add file-level summaries for further summarization in the chain
	normalizedResponse := strings.TrimSpace(orderedListAbuse.ReplaceAllString("\n"+response, " "))
	normalizedResponse = unorderedListAbuse.ReplaceAllString(normalizedResponse, " ")
	normalizedResponse = repeatedWhitespace.ReplaceAllString(normalizedResponse, " ")
	return normalizedResponse
}

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
	prDiff, err := diff.ParseMultiFileDiff(buf.Bytes())
	if err != nil {
		return nil, fmt.Errorf("diff: %w", err)
	}
	history := History{
		SystemMessage(fileDiffPrompt),
	}
	chunks := []string{}
	for _, fd := range prDiff {
		singleFileDiff, err := diff.PrintFileDiff(fd)
		if err != nil {
			return nil, err
		}
		if strings.HasSuffix(fd.NewName, "go.sum") {
			// this is auto-generated data, not really useful
			continue
		}
		if strings.HasSuffix(fd.NewName, "go.work.sum") {
			// this is auto-generated data, not really useful
			continue
		}
		logger.Debugf(ctx, "file diff: %s", singleFileDiff)
		history, err = lln.Talk(ctx, history.With(UserMessage(singleFileDiff)))
		if err != nil {
			return nil, err
		}
		response := history.Last()
		logger.Debugf(ctx, "LLM file summary: %s", response)
		// add file-level summaries for further summarization in the chain
		chunks = append(chunks, lln.normalizedResponse(response))
	}
	details := strings.Join(chunks, "\n\n")
	logger.Debugf(ctx, "LLM overall summary: %s", details)
	history, err = lln.Talk(ctx, History{
		SystemMessage(reduceDiffPrompt),
		UserMessage(details),
	})
	if err != nil {
		return nil, err
	}
	return history, nil
}
