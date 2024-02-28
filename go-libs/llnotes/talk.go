package llnotes

import (
	"context"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databricks/databricks-sdk-go/httpclient"
	"github.com/databricks/databricks-sdk-go/service/serving"
	"github.com/databrickslabs/sandbox/go-libs/github"
)

type Settings struct {
	GitHub     github.GitHubConfig
	Databricks config.Config
	Org, Repo  string
	Start, End string
	Model      string
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
	return &llNotes{
		http:  httpclient.NewApiClient(httpclient.ClientConfig{}),
		gh:    github.NewClient(&cfg.GitHub),
		w:     w,
		model: cfg.Model,
		org:   cfg.Org,
		repo:  cfg.Repo,
	}, nil
}

type llNotes struct {
	w     *databricks.WorkspaceClient
	gh    *github.GitHubClient
	http  *httpclient.ApiClient
	model string
	org   string
	repo  string
}

func (lln *llNotes) Talk(ctx context.Context, h History) (History, error) {
	response, err := lln.w.ServingEndpoints.Query(ctx, serving.QueryEndpointInput{
		Name:     lln.model,
		Messages: h.Messages(),
	})
	if err != nil {
		return nil, err
	}
	for _, v := range response.Choices {
		h = h.With(AssistantMessage(v.Message.Content))
	}
	return h, nil
}
