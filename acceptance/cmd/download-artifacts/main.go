package main

import (
	"archive/zip"
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/go-libs/github"
)

func main() {
	logger.DefaultLogger = &logger.SimpleLogger{
		Level: logger.LevelDebug,
	}
	d, err := New()
	if err != nil {
		panic(err)
	}
	err = d.run(context.Background())
	if err != nil {
		panic(err)
	}
}

type downloader struct {
	gh *github.GitHubClient
}

func New() (*downloader, error) {
	return &downloader{gh: github.NewClient(&github.GitHubConfig{})}, nil
}

type testResult struct {
	ecosystem.TestResult
	Branch string `json:"branch"`
	SHA    string `json:"sha"`
}

func (d *downloader) run(ctx context.Context) error {
	var results []testResult
	it := d.gh.ListArtifacts(ctx, "databrickslabs", "ucx")
	for it.HasNext(ctx) {
		artifact, err := it.Next(ctx)
		if err != nil {
			return fmt.Errorf("next: %w", err)
		}
		if artifact.Expired {
			continue
		}
		logger.Debugf(ctx, "Downloading %s", artifact.Name)
		buf, err := d.gh.DownloadArtifact(ctx, "databrickslabs", "ucx", artifact.ID)
		if err != nil {
			return fmt.Errorf("download: %w", err)
		}
		zr, err := zip.NewReader(bytes.NewReader(buf.Bytes()), artifact.SizeInBytes)
		if err != nil {
			return fmt.Errorf("zip: read: %w", err)
		}
		reader, err := zr.Open("test-report.json")
		if err != nil {
			return fmt.Errorf("zip: test-report.json: %w", err)
		}
		defer reader.Close()
		scanner := bufio.NewScanner(reader)
		bufSize := 1024 * 1024 * 50
		scanner.Buffer(make([]byte, bufSize), bufSize)
		for scanner.Scan() {
			var line testResult
			err = json.Unmarshal(scanner.Bytes(), &line)
			if err != nil {
				return fmt.Errorf("zip: test-report.json: json: %w", err)
			}
			line.Branch = artifact.WorflowRun.HeadBranch
			line.SHA = artifact.WorflowRun.HeadSHA
			results = append(results, line)
		}
		if err := scanner.Err(); err != nil {
			return fmt.Errorf("zip: test-report.json: scan: %w", err)
		}
		logger.Debugf(ctx, "num results %d", len(results))
	}

	file, err := os.OpenFile("/tmp/ucx-results.json", os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}
	defer file.Close()
	enc := json.NewEncoder(file)
	for _, v := range results {
		err := enc.Encode(v)
		if err != nil {
			return fmt.Errorf("encode: %w", err)
		}
	}

	logger.Debugf(ctx, "num results %d", len(results))
	return nil
}
