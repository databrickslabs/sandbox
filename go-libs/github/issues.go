package github

import "time"

type ListIssues struct {
	Milestone string    `url:"milestone,omitempty"`
	State     string    `url:"state,omitempty"`
	Assignee  string    `url:"assignee,omitempty"`
	Creator   string    `url:"creator,omitempty"`
	Mentioned string    `url:"mentioned,omitempty"`
	Labels    []string  `url:"labels,omitempty,comma"`
	Sort      string    `url:"sort,omitempty"`
	Direction string    `url:"direction,omitempty"`
	Since     time.Time `url:"since,omitempty"`
	PageOptions
}

type Issue struct {
	ID                int64      `json:"id,omitempty"`
	Number            int        `json:"number,omitempty"`
	State             string     `json:"state,omitempty"`
	Locked            bool       `json:"locked,omitempty"`
	Title             string     `json:"title,omitempty"`
	Body              string     `json:"body,omitempty"`
	AuthorAssociation string     `json:"author_association,omitempty"`
	User              *User      `json:"user,omitempty"`
	Labels            []Label    `json:"labels,omitempty"`
	Assignee          *User      `json:"assignee,omitempty"`
	Comments          int        `json:"comments,omitempty"`
	ClosedAt          time.Time  `json:"closed_at,omitempty"`
	CreatedAt         time.Time  `json:"created_at,omitempty"`
	UpdatedAt         time.Time  `json:"updated_at,omitempty"`
	ClosedBy          *User      `json:"closed_by,omitempty"`
	URL               string     `json:"url,omitempty"`
	HTMLURL           string     `json:"html_url,omitempty"`
	CommentsURL       string     `json:"comments_url,omitempty"`
	EventsURL         string     `json:"events_url,omitempty"`
	LabelsURL         string     `json:"labels_url,omitempty"`
	RepositoryURL     string     `json:"repository_url,omitempty"`
	Milestone         *Milestone `json:"milestone,omitempty"`
	Repository        *Repo      `json:"repository,omitempty"`
	Assignees         []User     `json:"assignees,omitempty"`
	NodeID            string     `json:"node_id,omitempty"`
}

type Milestone struct {
	URL          string    `json:"url,omitempty"`
	HTMLURL      string    `json:"html_url,omitempty"`
	LabelsURL    string    `json:"labels_url,omitempty"`
	ID           int64     `json:"id,omitempty"`
	Number       int       `json:"number,omitempty"`
	State        string    `json:"state,omitempty"`
	Title        string    `json:"title,omitempty"`
	Description  string    `json:"description,omitempty"`
	Creator      *User     `json:"creator,omitempty"`
	OpenIssues   int       `json:"open_issues,omitempty"`
	ClosedIssues int       `json:"closed_issues,omitempty"`
	CreatedAt    time.Time `json:"created_at,omitempty"`
	UpdatedAt    time.Time `json:"updated_at,omitempty"`
	ClosedAt     time.Time `json:"closed_at,omitempty"`
	DueOn        time.Time `json:"due_on,omitempty"`
	NodeID       string    `json:"node_id,omitempty"`
}

type IssueComment struct {
	ID        int64     `json:"id,omitempty"`
	NodeID    string    `json:"node_id,omitempty"`
	Body      string    `json:"body,omitempty"`
	User      User      `json:"user,omitempty"`
	CreatedAt time.Time `json:"created_at,omitempty"`
	UpdatedAt time.Time `json:"updated_at,omitempty"`
	// AuthorAssociation is the comment author's relationship to the issue's repository.
	// Possible values are "COLLABORATOR", "CONTRIBUTOR", "FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "MEMBER", "OWNER", or "NONE".
	AuthorAssociation string `json:"author_association,omitempty"`
	URL               string `json:"url,omitempty"`
	HTMLURL           string `json:"html_url,omitempty"`
	IssueURL          string `json:"issue_url,omitempty"`
}
