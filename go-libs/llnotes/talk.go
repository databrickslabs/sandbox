package llnotes

import (
	"context"
	"fmt"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databricks/databricks-sdk-go/httpclient"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databricks/databricks-sdk-go/service/serving"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/databrickslabs/sandbox/go-libs/sed"
)

type Settings struct {
	GitHub      github.GitHubConfig
	Databricks  config.Config
	Org, Repo   string
	Model       string
	MaxTokens   int
	Workers     int
	SkipLabels  []string
	SkipCommits []string
}

func New(cfg *Settings) (*llNotes, error) {
	cfg.Databricks.HTTPTimeoutSeconds = 300
	w, err := databricks.NewWorkspaceClient((*databricks.Config)(&cfg.Databricks))
	if err != nil {
		return nil, err
	}
	if cfg.Model == "" {
		cfg.Model = "databricks-mixtral-8x7b-instruct"
	}
	if cfg.MaxTokens == 0 {
		cfg.MaxTokens = 4000
	}
	if cfg.Workers == 0 {
		cfg.Workers = 15
	}
	if len(cfg.SkipLabels) == 0 {
		cfg.SkipLabels = []string{"internal"}
	}
	return &llNotes{
		http:  httpclient.NewApiClient(httpclient.ClientConfig{}),
		gh:    github.NewClient(&cfg.GitHub),
		w:     w,
		cfg:   cfg,
		model: cfg.Model,
		org:   cfg.Org,
		repo:  cfg.Repo,
		norm: sed.Pipeline{
			sed.Rule(`\\_`, `_`),
			sed.Rule(`\n([0-9])\. `, ` `),
			sed.Rule(`\n\s?- `, ` `),
			sed.Rule(`\n\s?\* `, ` `),
			sed.Rule(`\s+`, ` `),
		},
	}, nil
}

type llNotes struct {
	cfg   *Settings
	w     *databricks.WorkspaceClient
	gh    *github.GitHubClient
	http  *httpclient.ApiClient
	model string
	org   string
	repo  string
	norm  sed.Pipeline
}

func (lln *llNotes) Talk(ctx context.Context, h History) (History, error) {
	logger.Debugf(ctx, "Talking with AI:\n%s", h.Excerpt(80))
	response, err := lln.w.ServingEndpoints.Query(ctx, serving.QueryEndpointInput{
		Name:      lln.model,
		Messages:  h.Messages(),
		MaxTokens: lln.cfg.MaxTokens,
	})
	if err != nil {
		return nil, fmt.Errorf("llm: %w", err)
	}
	for _, v := range response.Choices {
		h = h.With(AssistantMessage(v.Message.Content))
	}
	return h, nil
}
