package cmd

import (
	"context"

	"github.com/databrickslabs/sandbox/go-libs/lite"
	"github.com/databrickslabs/sandbox/metascan/internal"
	"github.com/spf13/pflag"
)

const productName = "metascan"
const productVersion = "0.0.1"

func Run(ctx context.Context) {
	lite.New[internal.Config](ctx, lite.Init[internal.Config]{
		Name:       productName,
		Version:    productVersion,
		Short:      "Synchronise metadata across sandbox repositories",
		Long:       "",
		ConfigPath: "$HOME/.databricks/labs/metascan/config",
		EnvPrefix:  "DATABRICKS_LABS_METASCAN",
		Bind: func(flags *pflag.FlagSet, cfg *internal.Config) {
			//..
		},
	}).With(
		newScan(),
		newClone(),
	).Run(ctx)
}
