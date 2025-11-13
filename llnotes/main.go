package main

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/lite"
	"github.com/databrickslabs/sandbox/go-libs/llnotes"
	"github.com/fatih/color"
	"github.com/spf13/pflag"
)

const productName = "llnotes"
const productVersion = "0.0.2"

func main() {
	ctx := context.Background()
	databricks.WithProduct(productName, productVersion)
	lite.New(ctx, lite.Init[llnotes.Settings]{
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
			flags.StringVar(&cfg.Databricks.Profile, "profile", "", "Databricks config profile")
			flags.StringVar(&cfg.Model, "model", "databricks-claude-sonnet-4-5", "Serving chat model")
			flags.StringVar(&cfg.Org, "org", "databrickslabs", "GitHub org")
			flags.StringVar(&cfg.Repo, "repo", "ucx", "GitHub repository")
		},
	}).With(
		newPullRequest(),
		newUpcomingRelease(),
		newDiff(),
		newAnnounce(),
	).Run(ctx)
}

func newPullRequest() lite.Registerable[llnotes.Settings] {
	type req struct {
		number int
	}
	return &lite.Command[llnotes.Settings, req]{
		Name:  "pull-request",
		Short: "Generates a description for a pull request",
		Flags: func(flags *pflag.FlagSet, req *req) {
			flags.IntVar(&req.number, "number", 0, "Pull request number")
		},
		Run: func(root *lite.Root[llnotes.Settings], req *req) error {
			lln, err := llnotes.New(&root.Config)
			if err != nil {
				return err
			}
			ctx := root.Context()
			h, err := lln.PullRequest(ctx, req.number)
			if err != nil {
				return err
			}
			for {
				logger.Infof(ctx, h.Last())
				msg := fmt.Sprintf(
					" %s $ Tell me if I should rewrite it? Empty response would mean I stop. Type `save` to modify description.\n $",
					strings.ToUpper(root.Config.Model))
				reply := askFor(msg)
				if reply == "" {
					return nil
				}
				if strings.ToLower(reply) == "save" {
					return lln.EditPullRequest(ctx, req.number, h)
				}
				h, err = lln.Talk(ctx, h.With(llnotes.UserMessage(reply)))
				if err != nil {
					return err
				}
			}
		},
	}
}

func newUpcomingRelease() lite.Registerable[llnotes.Settings] {
	type req struct {
	}
	return &lite.Command[llnotes.Settings, req]{
		Name:  "upcoming-release",
		Short: "generates release notes",
		Run: func(root *lite.Root[llnotes.Settings], req *req) error {
			lln, err := llnotes.New(&root.Config)
			if err != nil {
				return err
			}
			ctx := root.Context()
			notes, err := lln.UpcomingRelease(ctx)
			if err != nil {
				return err
			}
			for _, v := range notes {
				fmt.Fprintf(root.OutOrStdout(), " * %s\n", v)
			}
			return nil
		},
	}
}

func newDiff() lite.Registerable[llnotes.Settings] {
	type req struct {
		since, until string
	}
	return &lite.Command[llnotes.Settings, req]{
		Name:  "diff",
		Short: "generates release notes between --since and --until",
		Flags: func(flags *pflag.FlagSet, req *req) {
			flags.StringVar(&req.since, "since", "", "Starting git reference (commit, tag, branch)")
			flags.StringVar(&req.until, "until", "main", "Ending git reference (commit, tag, branch)")
		},
		Run: func(root *lite.Root[llnotes.Settings], req *req) error {
			lln, err := llnotes.New(&root.Config)
			if err != nil {
				return err
			}
			ctx := root.Context()
			notes, err := lln.ReleaseNotesDiff(ctx, req.since, req.until)
			if err != nil {
				return err
			}
			for _, v := range notes {
				if strings.HasPrefix(v, "Release ") {
					continue
				}
				if strings.HasPrefix(v, "Bump ") {
					continue
				}
				fmt.Fprintf(root.OutOrStdout(), " * %s\n", v)
			}
			return nil
		},
	}
}

func newAnnounce() lite.Registerable[llnotes.Settings] {
	type req struct {
		version string
	}
	return &lite.Command[llnotes.Settings, req]{
		Name:  "announce",
		Short: "Generates release announcement",
		Flags: func(flags *pflag.FlagSet, req *req) {
			flags.StringVar(&req.version, "version", "", "Version to announce")
		},
		Run: func(root *lite.Root[llnotes.Settings], req *req) error {
			lln, err := llnotes.New(&root.Config)
			if err != nil {
				return err
			}
			ctx := root.Context()
			h, err := lln.Announce(ctx, req.version)
			if err != nil {
				return err
			}
			for {
				logger.Infof(ctx, h.Last())
				msg := fmt.Sprintf(
					" %s $ Tell me if I should rewrite it? Empty response would mean I stop.\n $",
					strings.ToUpper(root.Config.Model))
				reply := askFor(msg)
				if reply == "" {
					return nil
				}
				h, err = lln.Talk(ctx, h.With(llnotes.UserMessage(reply)))
				if err != nil {
					return err
				}
			}
		},
	}
}

var cliInput io.Reader = os.Stdin
var cliOutput io.Writer = os.Stdout

func askFor(prompt string) string {
	var s string
	r := bufio.NewReader(cliInput)
	for {
		fmt.Fprint(cliOutput, color.GreenString(prompt)+" ")
		s, _ = r.ReadString('\n')
		if s != "" {
			break
		}
	}
	return strings.TrimSpace(s)
}
