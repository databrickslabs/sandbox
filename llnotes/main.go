package main

import (
	"context"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/databrickslabs/sandbox/go-libs/lite"
	"github.com/databrickslabs/sandbox/go-libs/llnotes"
	"github.com/spf13/pflag"
)

const productName = "llnotes"
const productVersion = "0.0.1"

type settings struct {
	GitHub     github.GitHubConfig
	Profile    string
	Org, Repo  string
	Start, End string
	Model      string
}

func main() {
	ctx := context.Background()
	databricks.WithProduct(productName, productVersion)
	lite.New[settings](ctx, lite.Init[settings]{
		Name:       productName,
		Short:      "Release notes assistant",
		Version:    productVersion,
		ConfigPath: "$HOME/.databricks/labs/llnotes",
		Bind: func(flags *pflag.FlagSet, cfg *settings) {
			flags.StringVar(&cfg.GitHub.Pat, "github-token", "", "GitHub Personal Access token (that you have to rotate)")
			flags.Int64Var(&cfg.GitHub.ApplicationID, "github-app-id", 0, "GitHub App ID")
			flags.IntVar(&cfg.GitHub.InstallationID, "github-app-installation-id", 0, "GitHub App Installation ID")
			flags.StringVar(&cfg.GitHub.PrivateKeyPath, "github-app-private-key-path", "", "GitHub App Private Key file (*.pem) path")
			flags.StringVar(&cfg.GitHub.PrivateKeyBase64, "github-app-private-key", "", "GitHub App Private Key encoded in base64")
			flags.StringVar(&cfg.Profile, "profile", "DEFAULT", "Databricks config profile")
			flags.StringVar(&cfg.Org, "org", "databrickslabs", "GitHub org")
			flags.StringVar(&cfg.Repo, "repo", "ucx", "GitHub repository")
			flags.StringVar(&cfg.Start, "start", "", "Comparison start")
			flags.StringVar(&cfg.Model, "model", "databricks-mixtral-8x7b-instruct", "Serving chat model")

		},
	}).With(&lite.Command[settings, any]{
		Name: "generate",
		Run: func(cmd *lite.Root[settings], req *any) error {
			out, err := (&llnotes.ChangeDetector{
				Model:  cmd.Config.Model,
				GitHub: github.NewClient(&cmd.Config.GitHub),
				Databricks: &config.Config{
					Profile: cmd.Config.Profile,
				},
				Org:  cmd.Config.Org,
				Repo: cmd.Config.Repo,
			}).Run(ctx)
			if err != nil {
				return err
			}
			for _, v := range out {
				logger.Infof(ctx, v)
			}
			return nil
		},
	}).Run(ctx)
}
