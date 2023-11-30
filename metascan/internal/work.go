package internal

import (
	"fmt"
	"os"
	"path"
	"slices"
	"time"

	"github.com/adrg/frontmatter"
	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/folders"
)

func ProjectFileset() (fileset.FileSet, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return nil, err
	}
	root, err := folders.FindDirWithLeaf(cwd, ".github")
	if err != nil {
		return nil, err
	}
	return fileset.RecursiveChildren(root)
}

type Collection struct {
	root   fileset.FileSet
	Assets []Metadata
}

type Metadata struct {
	Title    string    `yaml:"title"`
	Language string    `yaml:"language"`
	Author   string    `yaml:"author"`
	Date     time.Time `yaml:"date"`
	Tags     []string  `yaml:"tags"`
	Maturity Maturity

	lastUpdated time.Time

	collection *Collection
	folder     string
}

func (m *Metadata) Name() string {
	return path.Base(m.folder)
}

func (m *Metadata) Validate() error {
	if len(m.Title) > 60 {
		return fmt.Errorf("title is larger than 60 characters: %s", m.Title)
	}
	if len(m.Tags) == 0 {
		return fmt.Errorf("no tags")
	}
	if len(m.Author) == 0 {
		return fmt.Errorf("no author")
	}
	if len(m.Language) == 0 {
		return fmt.Errorf("no language")
	}
	return nil
}

func (m *Metadata) LastUpdated() time.Time {
	return m.lastUpdated
}

func NewRepository() (*Collection, error) {
	fs, err := ProjectFileset()
	if err != nil {
		return nil, err
	}
	repo := &Collection{
		root: fs,
	}
	for _, readme := range fs.Filter(`README.md`) {
		var meta Metadata
		reader, err := readme.Open()
		if err != nil {
			return nil, err
		}
		_, err = frontmatter.Parse(reader, &meta)
		if err != nil {
			return nil, err
		}
		if meta.Title == "" {
			continue
		}
		meta.collection = repo
		meta.folder = path.Dir(readme.Relative)
		repo.Assets = append(repo.Assets, meta)
	}
	slices.SortFunc(repo.Assets, func(a, b Metadata) int {
		left := a.LastUpdated()
		right := b.LastUpdated()
		if left.Before(right) {
			return 1
		}
		return -1
	})
	return repo, nil
}
