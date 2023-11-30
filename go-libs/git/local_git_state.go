package git

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"

	"github.com/databricks/databricks-sdk-go/logger"
)

type LocalGitState struct {
	dir         string
	fetchRemote string
	pushRemote  string
}

func NewLocalGitState(dir string) (*LocalGitState, error) {
	l := &LocalGitState{
		dir: dir,
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

func (l *LocalGitState) cmd0(redirectStdout bool, args ...string) (string, error) {
	logger.Infof(context.Background(), "running: git %s", strings.Join(args, " "))
	cmd := exec.Command("git", args...)
	stdout := &bytes.Buffer{}
	cmd.Dir = l.dir
	cmd.Stdin = os.Stdin
	if redirectStdout {
		cmd.Stdout = io.MultiWriter(os.Stdout, stdout)
		cmd.Stderr = os.Stderr
	} else {
		cmd.Stdout = stdout
	}
	if err := cmd.Run(); err != nil {
		return "", err
	}
	return strings.TrimSpace(stdout.String()), nil
}

func (l *LocalGitState) cmd(args ...string) (string, error) {
	return l.cmd0(true, args...)
}

func (l *LocalGitState) getRemote(remoteType string) (string, error) {
	databricksOwners := []string{
		"databricks",
		"databrickslabs",
	}
	remotes, err := l.cmd0(false, "remote", "-v")
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

func (l *LocalGitState) CurrentBranch() (string, error) {
	return l.cmd("branch", "--show-current")
}

func (l *LocalGitState) CheckoutMain() (string, error) {
	return l.cmd("checkout", "main")
}

func (l *LocalGitState) ResetHard() (string, error) {
	return l.cmd("reset", "--hard")
}

func (l *LocalGitState) Clean() (string, error) {
	return l.cmd("clean", "-fdx")
}

func (l *LocalGitState) AddAll() (string, error) {
	return l.cmd("add", "--all")
}

func (l *LocalGitState) Commit(msg string) (string, error) {
	return l.cmd("commit", "-a", "-m", msg)
}

func (l *LocalGitState) FetchOrigin() (string, error) {
	return l.cmd("fetch", l.fetchRemote)
}

func (l *LocalGitState) PullOrigin() (string, error) {
	return l.cmd("pull", l.fetchRemote)
}

func (l *LocalGitState) CreateTag(v, msg string) (string, error) {
	return l.cmd("tag", v, "-f", "-m", msg)
}

func (l *LocalGitState) PushTag(v string) (string, error) {
	return l.cmd("push", l.pushRemote, v, "-f")
}
