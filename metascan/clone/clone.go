package clone

import (
	"context"
	"fmt"
	"path"
	"sort"
	"strings"

	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/git"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/databrickslabs/sandbox/metascan/inventory"
	"github.com/databrickslabs/sandbox/metascan/metadata"
	"github.com/yuin/goldmark"
	meta "github.com/yuin/goldmark-meta"
	"github.com/yuin/goldmark/parser"
	"github.com/yuin/goldmark/text"
)

type Clones []*Clone

func (cc Clones) Metadatas(ctx context.Context) (out []metadata.Metadata, err error) {
	for _, c := range cc {
		m, err := c.Metadatas(ctx)
		if err != nil {
			return nil, err
		}
		out = append(out, m...)
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].LastUpdated.After(out[j].LastUpdated)
	})
	return out, nil
}

type Clone struct {
	Inventory inventory.Item
	Git       *git.Checkout
	Repo      github.Repo
	FileSet   fileset.FileSet
}

func (c *Clone) Name() string {
	return fmt.Sprintf("%s/%s", c.Inventory.Org, c.Repo.Name)
}

func (c *Clone) Metadatas(ctx context.Context) ([]metadata.Metadata, error) {
	markdown := goldmark.New(
		goldmark.WithExtensions(
			meta.Meta,
		),
		goldmark.WithParserOptions(
			parser.WithAutoHeadingID(),
		),
	)
	if c.Inventory.IsSandbox {
		history, err := c.Git.History(ctx)
		if err != nil {
			return nil, err
		}
		out := []metadata.Metadata{}
		readmes := c.FileSet.Filter(`README.md`)
		for _, readme := range readmes {
			folder := path.Dir(readme.Relative)
			if folder == "." {
				continue
			}
			subHistory := history.Filter(func(pathname string) bool {
				if strings.HasSuffix(pathname, ".md") {
					// exclude any documentation
					return false
				}
				return strings.HasPrefix(pathname, folder)
			})
			authors := subHistory.Authors()
			raw, err := readme.Raw()
			if err != nil {
				return nil, err
			}
			document := markdown.Parser().Parse(text.NewReader(raw))
			doc := document.OwnerDocument()
			child := doc.FirstChild()
			title := string(child.Text(raw))
			if title == "" {
				continue
			}
			if len(authors) == 0 {
				continue
			}
			// todo: need the rest of the readme file
			out = append(out, metadata.Metadata{
				Title:       title,
				Author:      authors.Primary(),
				Language:    subHistory.Language(),
				Date:        subHistory.Started(),
				LastUpdated: subHistory.Ended(),
				Maturity:    c.Inventory.Maturity,
				URL:         fmt.Sprintf("%s/%s", c.Repo.HtmlURL, folder),
			})
		}
		return out, nil
	}
	return []metadata.Metadata{{
		Title:    c.Repo.Description,
		Tags:     c.Repo.Topics,
		Language: c.Repo.Langauge,
		Date:     c.FileSet.LastUpdated(),
		Maturity: c.Inventory.Maturity,
		URL:      c.Repo.HtmlURL,
	}}, nil
}

func (c *Clone) Maintainers(ctx context.Context) ([]string, error) {
	history, err := c.Git.History(ctx)
	if err != nil {
		return nil, err
	}
	authors := history.Authors()
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
