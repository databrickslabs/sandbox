package internal

import (
	"encoding/json"
	"os"
	"strings"
)

type handle struct {
	GhName string `json:"gh_name"`
	Email  string `json:"email"`
	Author string `json:"author"`
}

func LoadMapping(loc string) (out authorMapping) {
	raw, err := os.ReadFile(loc)
	if err != nil {
		return authorMapping{
			AdditionalMapping: map[string]string{},
		}
	}
	err = json.Unmarshal(raw, &out)
	if err != nil {
		return authorMapping{
			AdditionalMapping: map[string]string{},
		}
	}
	return out
}

type authorMapping struct {
	AdditionalMapping map[string]string `json:"additional_mapping"`
	Handles           []handle          `json:"handles"`
}

func (a authorMapping) LookupEmail(email, author string) string {
	email = strings.ToLower(email)
	author = strings.ToLower(author)
	cleanEmail, ok := a.AdditionalMapping[email]
	if ok {
		email = cleanEmail
	}
	cleanEmail, ok = a.AdditionalMapping[author]
	if ok {
		author = cleanEmail
	}
	for _, v := range a.Handles {
		if v.Email == email {
			return v.Email
		}
		if v.Email == author {
			return v.Email
		}
		if strings.ToLower(v.Author) == email {
			return v.Email
		}
		if strings.ToLower(v.Author) == author {
			return v.Email
		}
		if v.GhName == email {
			return v.Email
		}
		if v.GhName == author {
			return v.Email
		}
	}
	return email
}

func (a authorMapping) LookupAuthor(email, author string) string {
	clean := a.LookupEmail(email, author)
	for _, v := range a.Handles {
		if v.Email == clean {
			return v.Author
		}
	}
	return author
}

func (a authorMapping) LookupGhName(email, author string) string {
	clean := a.LookupEmail(email, author)
	for _, v := range a.Handles {
		if v.Email == clean {
			return v.GhName
		}
	}
	return "unknown"
}
