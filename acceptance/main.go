package main

import (
	"encoding/json"

	"github.com/sethvargo/go-githubactions"
)

func main() {
	a := githubactions.New()

	ghc, err := githubactions.Context()
	if err != nil {
		a.Errorf(err.Error())
	}

	org, repo := ghc.Repo()
	a.Debugf("this is debug")
	a.Infof("Org: %s, Repo: %s, Actor: %s, Workflow: %s, Ref: %s, ref name: %s", org, repo, ghc.Actor, ghc.Workflow, ghc.Ref, ghc.RefName)
	raw, err := json.MarshalIndent(ghc.Event, "", "  ")
	if err != nil {
		a.Errorf(err.Error())
	}
	a.Infof("event: %s", string(raw))
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
