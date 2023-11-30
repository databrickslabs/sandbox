package internal

import (
	"context"
	"fmt"

	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/git"
	"github.com/databrickslabs/sandbox/go-libs/github"
)

type Clones []*Clone

type Clone struct {
	Inventory Item
	Git       *git.Checkout
	Repo      github.Repo
	FileSet   fileset.FileSet
}

func (c Clone) Name() string {
	return fmt.Sprintf("%s/%s", c.Inventory.Org, c.Repo.Name)
}

func (c Clone) Maintainers(ctx context.Context) ([]string, error) {
	history, err := c.Git.History(ctx)
	if err != nil {
		return nil, err
	}
	authors := history.ContributorsRaw()
	atMost := 2
	if atMost > len(authors) {
		atMost = len(authors)
	}
	// TODO: build up author stats remapper
	var out []string
	for _, v := range authors {
		if v.Email == "action@github.com" {
			continue
		}
		if v.Author == "dependabot[bot]" {
			continue
		}
		out = append(out, v.Author)
	}
	return out[:atMost], nil
}
