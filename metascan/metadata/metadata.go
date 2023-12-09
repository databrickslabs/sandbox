package metadata

import (
	"fmt"
	"time"

	"github.com/databrickslabs/sandbox/metascan/inventory"
)

type Metadata struct {
	Title       string    `yaml:"title"`
	Language    string    `yaml:"language"`
	Author      string    `yaml:"author"`
	Date        time.Time `yaml:"date"` // TODO: rename to created_at
	LastUpdated time.Time `yaml:"updated_at"`
	Tags        []string  `yaml:"tags"`
	Maturity    inventory.Maturity
	URL         string
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
