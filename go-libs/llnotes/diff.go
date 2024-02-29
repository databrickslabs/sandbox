package llnotes

import (
	"bytes"
	"context"
	"fmt"
	"strings"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/sourcegraph/go-diff/diff"
)

const fileDiffPrompt = `Do not hallucinate. 
You are Staff Software Engineer, and you are reviewing one file at a time in a unitified diff format. 
Do not use phrases like "In this diff", "In this pull request", or "In this file". 
Do not mention file names, because they are not relevant for the feature description.
If new methods are added, explain what these methods are doing. 
If existing funcitonality is changed, explain the scope of these changes.
Please summarize the input as a signle paragraph of text written in American English. 
Your target audience is software engineers, who adopt your project.
If the prompt contains ordered or unordered lists, rewrite the entire response as a paragraph of text.`

const reduceDiffPrompt = `Do not hallucinate. 
You are a professional Technical Writer writing feature change description for the open-source library.
Do not use file names, because they are not relevant for the feature description.
Do not use phrases like "In this release".
Your target audience is software engineers. 
You receive a change description from your software engineering team about the newly developed features. 
Write a one-paragraph summary of this change for the release notes. 
It has to be one paragraph of text, because it will be included in a bigger document.`

func (lln *llNotes) normalizedResponse(response string) string {
	// add file-level summaries for further summarization in the chain
	return strings.TrimSpace(lln.norm.Apply("\n" + response))
}

func (lln *llNotes) explainDiff(ctx context.Context, history History, buf *bytes.Buffer) (History, error) {
	prDiff, err := diff.ParseMultiFileDiff(buf.Bytes())
	if err != nil {
		return nil, fmt.Errorf("parse: %w", err)
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
		logger.Debugf(ctx, "file diff for %s: %s", fd.NewName, singleFileDiff)
		history, err = lln.Talk(ctx, history.With(UserMessage(singleFileDiff)))
		if err != nil {
			return nil, fmt.Errorf("file diff: %w", err)
		}
		response := history.Last()
		logger.Debugf(ctx, "LLM summary for %s: %s", fd.NewName, response)
		// add file-level summaries for further summarization in the chain
		chunks = append(chunks, lln.normalizedResponse(response))
	}
	details := strings.Join(chunks, "\n")
	logger.Debugf(ctx, "LLM overall summary: %s", details)
	history, err = lln.Talk(ctx, History{
		SystemMessage(reduceDiffPrompt),
		UserMessage(details),
	})
	if err != nil {
		return nil, fmt.Errorf("summary: %w", err)
	}
	return history, nil
}
