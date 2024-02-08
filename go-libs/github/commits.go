package github

import "time"

type ListCommits struct {
	Base   string    `url:"sha,omitempty"`
	Path   string    `url:"path,omitempty"`
	Author string    `url:"author,omitempty"`
	Since  time.Time `url:"since,omitempty"`
	Until  time.Time `url:"until,omitempty"`
	PageOptions
}

type CommitAuthor struct {
	Date  time.Time `json:"date,omitempty"`
	Name  string    `json:"name,omitempty"`
	Email string    `json:"email,omitempty"`
}

type User struct {
	Login   string `json:"login,omitempty"`
	Name    string `json:"name,omitempty"`
	Company string `json:"company,omitempty"`
	Email   string `json:"email,omitempty"`
	Type    string `json:"type,omitempty"`
}

type SignatureVerification struct {
	Verified  bool   `json:"verified,omitempty"`
	Reason    string `json:"reason,omitempty"`
	Signature string `json:"signature,omitempty"`
	Payload   string `json:"payload,omitempty"`
}

type Commit struct {
	SHA          string                `json:"sha,omitempty"`
	Author       CommitAuthor          `json:"author,omitempty"`
	Committer    CommitAuthor          `json:"committer,omitempty"`
	Message      string                `json:"message,omitempty"`
	Parents      []Commit              `json:"parents,omitempty"`
	Verification SignatureVerification `json:"verification,omitempty"`
}

type RepositoryCommit struct {
	SHA         string   `json:"sha,omitempty"`
	Commit      Commit   `json:"commit,omitempty"`
	Author      User     `json:"author,omitempty"`
	Committer   User     `json:"committer,omitempty"`
	Parents     []Commit `json:"parents,omitempty"`
	HTMLURL     string   `json:"html_url,omitempty"`
	URL         string   `json:"url,omitempty"`
	CommentsURL string   `json:"comments_url,omitempty"`
}
