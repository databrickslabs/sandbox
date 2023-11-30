package git

import (
	"context"
	"errors"
	"fmt"
	"strings"

	"github.com/databrickslabs/sandbox/go-libs/process"
)

type Checkout struct {
	dir         string
	fetchRemote string
	pushRemote  string
	ctx         context.Context
}

func NewCheckout(ctx context.Context, dir string) (*Checkout, error) {
	l := &Checkout{
		dir: dir,
		ctx: ctx,
	}
	var err error
	l.fetchRemote, err = l.getRemote("fetch")
	if err != nil {
		return nil, err
	}
	l.pushRemote, err = l.getRemote("push")
	if err != nil {
		return nil, err
	}
	return l, nil
}

func (l *Checkout) cmd(args ...string) (string, error) {
	args = append([]string{"git"}, args...)
	out, err := process.Background(l.ctx, args, process.WithDir(l.dir))
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(out), nil
}

func (l *Checkout) getRemote(remoteType string) (string, error) {
	databricksOwners := []string{
		"databricks",
		"databrickslabs",
	}
	remotes, err := l.cmd("remote", "-v")
	if err != nil {
		return "", err
	}
	// split on newlines
	for _, remote := range strings.Split(remotes, "\n") {
		// split on whitespace
		parts := strings.Fields(remote)
		if len(parts) != 3 {
			return "", fmt.Errorf("unexpected remote format: %s", remote)
		}
		if parts[2] != "("+remoteType+")" {
			continue
		}
		for _, owner := range databricksOwners {
			if strings.Contains(parts[1], ":"+owner+"/") {
				return parts[0], nil
			}
		}
	}
	return "", errors.New("no fetch remote found")
}

func (l *Checkout) CurrentBranch() (string, error) {
	return l.cmd("branch", "--show-current")
}

func (l *Checkout) CheckoutMain() (string, error) {
	return l.cmd("checkout", "main")
}

func (l *Checkout) ResetHard() (string, error) {
	return l.cmd("reset", "--hard")
}

func (l *Checkout) Clean() (string, error) {
	return l.cmd("clean", "-fdx")
}

func (l *Checkout) AddAll() (string, error) {
	return l.cmd("add", "--all")
}

func (l *Checkout) Commit(msg string) (string, error) {
	return l.cmd("commit", "-a", "-m", msg)
}

func (l *Checkout) FetchOrigin() (string, error) {
	return l.cmd("fetch", l.fetchRemote)
}

func (l *Checkout) PullOrigin() (string, error) {
	return l.cmd("pull", l.fetchRemote)
}

func (l *Checkout) CreateTag(v, msg string) (string, error) {
	return l.cmd("tag", v, "-f", "-m", msg)
}

func (l *Checkout) PushTag(v string) (string, error) {
	return l.cmd("push", l.pushRemote, v, "-f")
}
