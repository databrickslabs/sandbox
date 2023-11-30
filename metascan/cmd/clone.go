package cmd

import (
	"path/filepath"
	"sort"

	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/git"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/databrickslabs/sandbox/go-libs/lite"
	"github.com/databrickslabs/sandbox/go-libs/render"
	"github.com/databrickslabs/sandbox/metascan/internal"
	"github.com/spf13/pflag"
)

func newClone() lite.Registerable[internal.Config] {
	type cloneRequest struct {
		github.GitHubConfig
		mailmap string
	}
	return &lite.Command[internal.Config, cloneRequest]{
		Name:  "clone-all",
		Short: "Clones all repositories from inventory",
		Flags: func(flags *pflag.FlagSet, req *cloneRequest) {
			flags.StringVar(&req.Pat, "github-pat", "", "github pat token")
			flags.StringVar(&req.PrivateKeyPath, "github-private-key", "", "github private key path")
			flags.Int64Var(&req.ApplicationID, "github-application-id", 0, "github app id")
			flags.IntVar(&req.InstallationID, "github-installation-id", 0, "github app installation id")
			flags.StringVar(&req.mailmap, "mailmap", "", "mailmap file")
		},
		Run: func(cmd *lite.Root[internal.Config], req *cloneRequest) error {
			ctx := cmd.Context()
			home, err := env.UserHomeDir(ctx)
			if err != nil {
				return err
			}
			cacheDir := filepath.Join(home, ".databricks/labs/metascan/cache")
			globalInfo := internal.NewGlobalInfo(cacheDir, &req.GitHubConfig)
			clones, err := globalInfo.Checkout(ctx)
			if err != nil {
				return err
			}
			type tmp struct {
				Author, Email string
			}

			mailmap := internal.LoadMapping(req.mailmap)

			stats := map[tmp]int{}
			for _, c := range clones {
				history, err := c.Git.History(ctx)
				if err != nil {
					return err
				}
				for _, a := range history.ContributorsRaw() {
					email := mailmap.LookupEmail(a.Email, a.Author)
					author := mailmap.LookupAuthor(a.Email, a.Author)
					stats[tmp{author, email}] += a.Commits
				}
			}
			rows := []git.AuthorInfo{}
			for k, v := range stats {
				rows = append(rows, git.AuthorInfo{
					Author:  k.Author,
					Email:   k.Email,
					Commits: v,
				})
			}
			sort.Slice(rows, func(i, j int) bool {
				return rows[i].Commits > rows[j].Commits
			})
			return render.RenderTemplate(cmd.OutOrStdout(), statsTpl, rows)
		},
	}
}

const statsTpl = `AUTHOR	EMAIL	COMMITS{{range .}}
{{.Author}}	{{.Email}}	{{.Commits}}{{end}}`
