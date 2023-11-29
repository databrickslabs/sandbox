package render

import (
	"time"

	"github.com/briandowns/spinner"
	"github.com/fatih/color"
	"github.com/spf13/cobra"
)

func Spinner(cmd *cobra.Command) chan string {
	ctx := cmd.Context()
	isTTY := !color.NoColor
	var sp *spinner.Spinner
	if isTTY {
		charset := spinner.CharSets[11]
		sp = spinner.New(charset, 200*time.Millisecond,
			spinner.WithWriter(cmd.ErrOrStderr()),
			spinner.WithColor("green"))
		sp.Start()
	}
	updates := make(chan string)
	go func() {
		if isTTY {
			defer sp.Stop()
		}
		for {
			select {
			case <-ctx.Done():
				return
			case x, hasMore := <-updates:
				if isTTY {
					// `sp`` access is isolated to this method,
					// so it's safe to update it from this goroutine.
					sp.Suffix = " " + x
				}
				if !hasMore {
					return
				}
			}
		}
	}()
	return updates
}
