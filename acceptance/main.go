package main

import (
	"context"
	"encoding/json"

	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/sethvargo/go-githubactions"
)

func main() {
	a := githubactions.New()

	ghc, err := githubactions.Context()
	if err != nil {
		a.Errorf(err.Error())
	}

	gh := github.NewClient(&github.GitHubConfig{
		GitHubTokenSource: github.GitHubTokenSource{
			// Pat: a.Getenv("GITHUB_TOKEN"),
			Pat: ghc.Event["token"].(string),
		},
	})
	// also - there's OIDC integration:
	// a.GetIDToken(ctx, "api://AzureADTokenExchange")

	org, repo := ghc.Repo()
	a.Debugf("this is debug")
	a.Infof("Org: %s, Repo: %s, Actor: %s, Workflow: %s, Ref: %s, ref name: %s", org, repo, ghc.Actor, ghc.Workflow, ghc.Ref, ghc.RefName)
	raw, err := json.MarshalIndent(ghc.Event, "", "  ")
	if err != nil {
		a.Errorf(err.Error())
	}
	a.Infof("event: %s", string(raw))

	var event struct {
		PullRequest *github.PullRequest `json:"pull_request"`
	}
	err = json.Unmarshal(raw, &event)
	if err != nil {
		a.Errorf(err.Error())
	}
	ctx := context.Background()
	_, err = gh.CreateIssueComment(ctx, org, repo, event.PullRequest.Number, "Test from acceptance action")
	if err != nil {
		a.Errorf(err.Error())
	}

	a.Noticef("This is notice")
	a.Warningf("this is warning")
	a.Errorf("this is error")

	m := map[string]string{
		"file": "app.go",
		"line": "100",
	}
	a.WithFieldsMap(m).Errorf("an error message")

	a.SetOutput("sample", "foo")

	a.AddStepSummary(`
## Heading

- :rocket:
- :moon:
`)

	if err := a.AddStepSummaryTemplate(`
## Heading

- {{.Input}}
- :moon:
`, map[string]string{
		"Input": ":rocket:",
	}); err != nil {
		a.Errorf(err.Error())
	}
}
