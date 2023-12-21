package git

import (
	"context"
	"fmt"
	"strings"

	"github.com/databrickslabs/sandbox/go-libs/process"
)

type Checkout struct {
	dir         string
	fetchRemote string
	pushRemote  string
}

func NewCheckout(ctx context.Context, dir string) (*Checkout, error) {
	l := &Checkout{
		dir: dir,
	}
	remotes, err := l.remotes(ctx)
	if err != nil {
		return nil, err
	}
	l.fetchRemote = remotes["fetch"]
	l.pushRemote = remotes["push"]
	return l, nil
}

func (l *Checkout) cmd(ctx context.Context, args ...string) (string, error) {
	args = append([]string{"git"}, args...)
	out, err := process.Background(ctx, args, process.WithDir(l.dir))
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(out), nil
}

func (l *Checkout) Dir() string {
	return l.dir
}

func (l *Checkout) OrgAndRepo() (string, string, bool) {
	tmp := strings.TrimSuffix(l.fetchRemote, ".git")
	tmp = strings.TrimPrefix(tmp, "https://github.com/")
	tmp = strings.TrimPrefix(tmp, "git@github.com:")
	return strings.Cut(tmp, "/")
}

func (l *Checkout) remotes(ctx context.Context) (map[string]string, error) {
	remotes := map[string]string{
		"fetch": "origin",
		"push":  "origin",
	}
	raw, err := l.cmd(ctx, "remote", "-v")
	if err != nil {
		return nil, err
	}
	// split on newlines
	for _, remote := range strings.Split(raw, "\n") {
		// split on whitespace
		parts := strings.Fields(remote)
		if len(parts) != 3 {
			return nil, fmt.Errorf("unexpected remote format: %s", remote)
		}
		if parts[2][0] != '(' {
			continue
		}
		name := strings.Trim(parts[2], "()")
		remotes[name] = parts[1]
	}
	return remotes, nil
}

func (l *Checkout) CurrentBranch(ctx context.Context) (string, error) {
	return l.cmd(ctx, "branch", "--show-current")
}

func (l *Checkout) DefaultBranch(ctx context.Context) (string, error) {
	return l.cmd(ctx, "config", "--get", "init.defaultBranch")
}

func (l *Checkout) CheckoutMain(ctx context.Context) (string, error) {
	defaultBranch, err := l.DefaultBranch(ctx)
	if err != nil {
		return "", fmt.Errorf("default branch: %w", err)
	}
	return l.cmd(ctx, "checkout", defaultBranch)
}

// If prepare/X.X.X does not name an existing branch, this creates the new branch,
// pointing to the current commit, as if by regular git checkout -b. If prepare/X.X.X does name an
// existing branch, what happens instead is that Git forcibly re-points the branch name to the current commit.
//
// This is a lot like a git reset --soft. A branch name is really just a human-readable name for some Git hash ID,
// and a soft reset changes the hash ID attached to the branch name, without touching the index or work-tree. In
// the same way, git checkout -B will change the ID attached to this name, without touching the index or work-tree.
func (l *Checkout) ForceCheckout(ctx context.Context, branch string) (string, error) {
	return l.cmd(ctx, "checkout", "-B", branch)
}

func (l *Checkout) ResetHard(ctx context.Context) (string, error) {
	return l.cmd(ctx, "reset", "--hard")
}

func (l *Checkout) Clean(ctx context.Context) (string, error) {
	return l.cmd(ctx, "clean", "-fdx")
}

func (l *Checkout) AddAll(ctx context.Context) (string, error) {
	return l.cmd(ctx, "add", "--all")
}

func (l *Checkout) Commit(ctx context.Context, msg string) (string, error) {
	return l.cmd(ctx, "commit", "-a", "-m", msg)
}

func (l *Checkout) FetchOrigin(ctx context.Context) (string, error) {
	return l.cmd(ctx, "fetch", l.fetchRemote)
}

func (l *Checkout) PullOrigin(ctx context.Context) (string, error) {
	return l.cmd(ctx, "pull", l.fetchRemote)
}

func (l *Checkout) CreateTag(ctx context.Context, v, msg string) (string, error) {
	return l.cmd(ctx, "tag", v, "-f", "-m", msg)
}

func (l *Checkout) ForcePush(ctx context.Context, v string) (string, error) {
	return l.cmd(ctx, "push", l.pushRemote, v, "-f")
}
