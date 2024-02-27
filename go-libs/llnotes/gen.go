package llnotes

import (
	"context"
	"fmt"
	"strings"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/client"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databricks/databricks-sdk-go/service/serving"
	"github.com/databrickslabs/sandbox/go-libs/github"
)

type ChangeDetector struct {
	GitHub     *github.GitHubClient
	Databricks *config.Config
	Org, Repo  string
	Model      string
}

func (c *ChangeDetector) Run(ctx context.Context) ([]string, error) {
	versions, err := listing.ToSlice(ctx, c.GitHub.Versions(ctx, c.Org, c.Repo))
	if err != nil {
		return nil, fmt.Errorf("versions: %w", err)
	}
	repo, err := c.GitHub.GetRepo(ctx, c.Org, c.Repo)
	if err != nil {
		return nil, fmt.Errorf("get repo: %w", err)
	}
	latestTag := "v0.0.0" // special value for first-release projects
	if len(versions) > 0 {
		latestTag = versions[0].Version
	}
	commits, err := listing.ToSlice(ctx,
		c.GitHub.CompareCommits(ctx, c.Org, c.Repo, latestTag, repo.DefaultBranch))
	if err != nil {
		return nil, fmt.Errorf("compare commits: %w", err)
	}
	if c.Model == "" {
		c.Model = "databricks-mixtral-8x7b-instruct"
	}
	return c.tryChat2(ctx, commits)
}

func (c *ChangeDetector) tryChat2(ctx context.Context, commits []github.RepositoryCommit) ([]string, error) {
	w, err := databricks.NewWorkspaceClient((*databricks.Config)(c.Databricks))
	if err != nil {
		return nil, err
	}
	x := []string{}
	for _, c := range commits {
		x = append(x, c.Commit.Message)
	}
	response, err := w.ServingEndpoints.Query(ctx, serving.QueryEndpointInput{
		Name: c.Model,
		Messages: []serving.ChatMessage{
			{
				Role:    "system",
				Content: blogPrompt,
			},
			{
				Role:    "user",
				Content: strings.Join(x, "\n"),
			},
		},
	})
	if err != nil {
		return nil, err
	}
	out := []string{}
	for _, v := range response.Choices {
		out = append(out, v.Message.Content)
	}
	return out, nil
}

func (c *ChangeDetector) tryChat(ctx context.Context, client *client.DatabricksClient, commits []github.RepositoryCommit) error {
	api := &FoundationModelAPI{client}

	req := Invocation{
		Model: c.Model,
		Messages: []ChatMessage{
			{
				Role: RoleSystem,
				Content: fmt.Sprintf(`You received draft release notes for a new version of %s in a markdown format from multiple team members. 

				Once you get "WRITE RELEASE NOTES", take all the messages you've received, write them as release notes, and summarize the most important features, and mention them on top. Keep the markdown links when relevant.
				`, c.Repo),
			},
		},
	}
	for _, c := range commits {
		req.Messages = append(req.Messages, ChatMessage{
			Role:    RoleUser,
			Content: c.Commit.Message,
		})
	}
	req.Messages = append(req.Messages, ChatMessage{
		Role:    RoleUser,
		Content: "WRITE RELEASE NOTES",
	})
	res, err := api.Invoke(ctx, req)
	if err != nil {
		return fmt.Errorf("result: %w", err)
	}
	for _, v := range res.Choices {
		logger.Debugf(ctx, "Response: %s", v.Text)
	}
	return nil
}

func (c *ChangeDetector) tryCompletion(ctx context.Context, client *client.DatabricksClient, commits []github.RepositoryCommit) error {
	api := &FoundationModelAPI{client}

	prompt := []string{}
	prompt = append(prompt, fmt.Sprintf(`You received draft release notes for a new version of %s in a markdown format from multiple team members. 

	Please rewrite them like a professional technical writer, summarize the most important features, and mention them on top. Keep the markdown links when relevant.
	`, c.Repo))

	for _, c := range commits {
		prompt = append(prompt, c.Commit.Message)
	}
	res, err := api.Invoke(ctx, Invocation{
		Model:  c.Model,
		Prompt: prompt,
	})
	if err != nil {
		return fmt.Errorf("result: %w", err)
	}
	for _, v := range res.Choices {
		logger.Debugf(ctx, "Response: %s", v.Text)
	}
	return nil
}
