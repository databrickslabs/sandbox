package cmd

import (
	"fmt"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/lite"
	"github.com/databrickslabs/sandbox/go-libs/render"
	"github.com/databrickslabs/sandbox/metascan/internal"
	"github.com/spf13/pflag"
)

func newScan() lite.Registerable[internal.Config] {
	type scanRequest struct {
		fail bool
	}
	return &lite.Command[internal.Config, scanRequest]{
		Name:  "scan-this",
		Short: "Scans frontmatter of README.md files in current directory and shows summary",
		Flags: func(flags *pflag.FlagSet, req *scanRequest) {
			flags.BoolVar(&req.fail, "fail", false, "fail on validation errors")
		},
		Run: func(cmd *lite.Root[internal.Config], req *scanRequest) error {
			ctx := cmd.Context()
			repo, err := internal.NewRepository()
			if err != nil {
				return err
			}
			for _, m := range repo.Assets {
				err := m.Validate()
				if err != nil && req.fail {
					return fmt.Errorf("%s: %s", m.Name(), err)
				} else if err != nil {
					logger.Errorf(ctx, "%s: %s", m.Name(), err)
				}
			}
			return render.RenderTemplate(cmd.OutOrStdout(), scanTemplate, repo)
		},
	}
}

const scanTemplate = `Matirity	Name	Title	Author	Updated{{range .Assets}}
{{.Maturity}}	{{.Name}}	{{.Title}}	{{.Author}}	{{.LastUpdated.Format "2006-01-02"}}{{end}}
`
