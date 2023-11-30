package git

import (
	"context"
	"errors"
	"strings"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/process"
)

func LazyClone(ctx context.Context, repo, dir string) (*Checkout, error) {
	_, err := process.Background(ctx, []string{"git", "clone", repo, dir})
	if err == nil {
		return NewCheckout(ctx, dir)
	}
	var processErr *process.ProcessError
	if !errors.As(err, &processErr) {
		return nil, err
	}
	if strings.Contains(processErr.Stderr, "already exists") {
		checkout, err := NewCheckout(ctx, dir)
		if err != nil {
			return nil, err
		}
		res, err := checkout.PullOrigin(ctx)
		if err != nil {
			return nil, err
		}
		logger.Debugf(ctx, "updating checkout of %s: %s", repo, res)
		return checkout, nil
	}
	return nil, err
}
