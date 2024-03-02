package llnotes

import (
	"bytes"
	"context"
	"fmt"
	"sort"
	"strings"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/parallel"
	"github.com/sourcegraph/go-diff/diff"
)

const reduceDiffPrompt = `Do not hallucinate. 
You are a professional Technical Writer writing feature change description for the open-source library.
Do not use file names, because they are not relevant for the feature description.
Do not use phrases like "In this release".
Your target audience is software engineers. 
You receive a change description from your software engineering team about the newly developed features. 
Write a one-paragraph summary of this change for the release notes. 
It has to be one paragraph of text, because it will be included in a bigger document.`

func (lln *llNotes) explainDiff(ctx context.Context, history History, buf *bytes.Buffer) (History, error) {
	prDiff, err := diff.ParseMultiFileDiff(buf.Bytes())
	if err != nil {
		return nil, fmt.Errorf("parse: %w", err)
	}
	// TODO: bring back rst files after we can explain
	// https://github.com/databrickslabs/mosaic/commit/7cfcfcef709f6065cc3ad7ba208aa71664a10dfd
	ignoreSuffixes := []string{"go.sum", "go.work.sum", ".ipynb", ".rst"}
	var tasks []diffTask
	for i, fd := range prDiff {
		var ignore bool
		for _, suffix := range ignoreSuffixes {
			if strings.HasSuffix(fd.NewName, suffix) {
				ignore = true
			}
		}
		if ignore {
			continue
		}
		tasks = append(tasks, diffTask{i, len(prDiff), fd, history})
	}
	chunks, err := parallel.Tasks(ctx, lln.cfg.Workers, tasks, lln.fileDiffWork)
	if err != nil {
		return nil, fmt.Errorf("parallel: %w", err)
	}
	sort.Slice(chunks, func(i, j int) bool {
		return chunks[i].index < chunks[j].index
	})
	var notes []string
	for _, v := range chunks {
		notes = append(notes, v.message)
	}
	rawSummary := strings.Join(notes, "\n")
	if len(rawSummary) == 0 {
		rawSummary = "this commit was empty"
	}
	logger.Debugf(ctx, "LLM overall summary: %s", rawSummary)
	history, err = lln.Talk(ctx, History{
		SystemMessage(reduceDiffPrompt),
		UserMessage(rawSummary),
	})
	if err != nil {
		return nil, fmt.Errorf("summary: %w", err)
	}
	return history, nil
}

func (lln *llNotes) fileDiffWork(ctx context.Context, t diffTask) (*diffReply, error) {
	singleFileDiff, err := diff.PrintFileDiff(t.diff)
	if err != nil {
		return nil, fmt.Errorf("print: %s: %w", t.diff.NewName, err)
	}
	fileInfo := fmt.Sprintf("file %d/%d", t.index+1, t.total)
	logger.Debugf(ctx, "%s: %s", fileInfo, singleFileDiff)
	tokens := strings.Split(string(singleFileDiff), " ")
	if len(tokens) > 15_000 {
		tokens = tokens[:15_000]
		singleFileDiff = []byte(strings.Join(tokens, " "))
	}
	history, err := lln.Talk(ctx, t.history.With(UserMessage(singleFileDiff)))
	if err != nil {
		return nil, fmt.Errorf("summary: %s: %w", t.diff.NewName, err)
	}
	response := history.Last()
	logger.Debugf(ctx, "%s: summary for %s:\n%s", fileInfo, t.diff.NewName, response)
	normalized := strings.TrimSpace(lln.norm.Apply("\n" + response))
	return &diffReply{t.index, normalized}, nil
}

type diffTask struct {
	index   int
	total   int
	diff    *diff.FileDiff
	history History
}

type diffReply struct {
	index   int
	message string
}
