package main

import (
	"context"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/lite"
	"github.com/databrickslabs/sandbox/go-libs/llnotes"
	"github.com/spf13/pflag"
)

const productName = "llnotes"
const productVersion = "0.0.2"

func main() {
	ctx := context.Background()
	databricks.WithProduct(productName, productVersion)
	lite.New[llnotes.Settings](ctx, lite.Init[llnotes.Settings]{
		Name:       productName,
		Short:      "Release notes assistant",
		Version:    productVersion,
		ConfigPath: "$HOME/.databricks/labs/llnotes",
		Bind: func(flags *pflag.FlagSet, cfg *llnotes.Settings) {
			flags.StringVar(&cfg.GitHub.Pat, "github-token", "", "GitHub Personal Access token (that you have to rotate)")
			flags.Int64Var(&cfg.GitHub.ApplicationID, "github-app-id", 0, "GitHub App ID")
			flags.IntVar(&cfg.GitHub.InstallationID, "github-app-installation-id", 0, "GitHub App Installation ID")
			flags.StringVar(&cfg.GitHub.PrivateKeyPath, "github-app-private-key-path", "", "GitHub App Private Key file (*.pem) path")
			flags.StringVar(&cfg.GitHub.PrivateKeyBase64, "github-app-private-key", "", "GitHub App Private Key encoded in base64")
			flags.StringVar(&cfg.Databricks.Profile, "profile", "DEFAULT", "Databricks config profile")
			flags.StringVar(&cfg.Model, "model", "databricks-mixtral-8x7b-instruct", "Serving chat model")
			flags.StringVar(&cfg.Org, "org", "databrickslabs", "GitHub org")
			flags.StringVar(&cfg.Repo, "repo", "ucx", "GitHub repository")
		},
	}).With(
		newPullRequest(),
		newReleaseNotes(),
		newCommit(),
	).Run(ctx)
}

func newPullRequest() lite.Registerable[llnotes.Settings] {
	type req struct {
		number int
	}
	return &lite.Command[llnotes.Settings, req]{
		Name: "pull-request",
		Flags: func(flags *pflag.FlagSet, req *req) {
			flags.IntVar(&req.number, "number", 0, "Pull request number")
		},
		Run: func(root *lite.Root[llnotes.Settings], req *req) error {
			lln, err := llnotes.New(&root.Config)
			if err != nil {
				return err
			}
			h, err := lln.PullRequest(root.Context(), req.number)
			if err != nil {
				return err
			}
			logger.Infof(root.Context(), h.Last())
			return nil
		},
	}
}

func newReleaseNotes() lite.Registerable[llnotes.Settings] {
	type req struct {
	}
	return &lite.Command[llnotes.Settings, req]{
		Name: "release-notes",
		Run: func(root *lite.Root[llnotes.Settings], req *req) error {
			lln, err := llnotes.New(&root.Config)
			if err != nil {
				return err
			}
			h, err := lln.ReleaseNotes(root.Context())
			if err != nil {
				return err
			}
			logger.Infof(root.Context(), h.Last())
			return nil
		},
	}
}

func newCommit() lite.Registerable[llnotes.Settings] {
	type req struct {
		sha string
	}
	return &lite.Command[llnotes.Settings, req]{
		Name: "commit",
		Flags: func(flags *pflag.FlagSet, req *req) {
			flags.StringVar(&req.sha, "sha", "", "Commit hash")
		},
		Run: func(root *lite.Root[llnotes.Settings], req *req) error {
			lln, err := llnotes.New(&root.Config)
			if err != nil {
				return err
			}
			h, err := lln.CommitBySHA(root.Context(), req.sha)
			if err != nil {
				return err
			}
			logger.Infof(root.Context(), h.Last())
			return nil
		},
	}
}
