package github

import "time"

type PageOptions struct {
	Page    int `url:"page,omitempty"`
	PerPage int `url:"per_page,omitempty"`
}

type iteratableRequest interface {
	defaults()
	increment()
}

func (po *PageOptions) defaults() {
	po.Page = 1
	po.PerPage = 100
}

func (po *PageOptions) increment() {
	po.Page++
}

type ListPullRequests struct {
	State     string `url:"state,omitempty"`
	Head      string `url:"head,omitempty"`
	Base      string `url:"base,omitempty"`
	Sort      string `url:"sort,omitempty"`
	Direction string `url:"direction,omitempty"`

	PageOptions
}

type PullRequestAutoMerge struct {
	EnabledBy     User   `json:"enabled_by,omitempty"`
	MergeMethod   string `json:"merge_method,omitempty"`
	CommitTitle   string `json:"commit_title,omitempty"`
	CommitMessage string `json:"commit_message,omitempty"`
}

type PullRequestBranch struct {
	Label string `json:"label,omitempty"`
	Ref   string `json:"ref,omitempty"`
	SHA   string `json:"sha,omitempty"`
	Repo  Repo   `json:"repo,omitempty"`
	User  User   `json:"user,omitempty"`
}

type PullRequest struct {
	ID                  int64                `json:"id,omitempty"`
	Number              int                  `json:"number,omitempty"`
	State               string               `json:"state,omitempty"`
	Locked              bool                 `json:"locked,omitempty"`
	Title               string               `json:"title,omitempty"`
	Body                string               `json:"body,omitempty"`
	CreatedAt           time.Time            `json:"created_at,omitempty"`
	UpdatedAt           time.Time            `json:"updated_at,omitempty"`
	ClosedAt            time.Time            `json:"closed_at,omitempty"`
	MergedAt            time.Time            `json:"merged_at,omitempty"`
	Labels              []Label              `json:"labels,omitempty"`
	User                User                 `json:"user,omitempty"`
	Draft               bool                 `json:"draft,omitempty"`
	Merged              bool                 `json:"merged,omitempty"`
	Mergeable           bool                 `json:"mergeable,omitempty"`
	MergeableState      string               `json:"mergeable_state,omitempty"`
	MergedBy            User                 `json:"merged_by,omitempty"`
	MergeCommitSHA      string               `json:"merge_commit_sha,omitempty"`
	Rebaseable          bool                 `json:"rebaseable,omitempty"`
	Comments            int                  `json:"comments,omitempty"`
	Commits             int                  `json:"commits,omitempty"`
	Additions           int                  `json:"additions,omitempty"`
	Deletions           int                  `json:"deletions,omitempty"`
	ChangedFiles        int                  `json:"changed_files,omitempty"`
	URL                 string               `json:"url,omitempty"`
	HTMLURL             string               `json:"html_url,omitempty"`
	IssueURL            string               `json:"issue_url,omitempty"`
	StatusesURL         string               `json:"statuses_url,omitempty"`
	DiffURL             string               `json:"diff_url,omitempty"`
	PatchURL            string               `json:"patch_url,omitempty"`
	CommitsURL          string               `json:"commits_url,omitempty"`
	CommentsURL         string               `json:"comments_url,omitempty"`
	ReviewCommentsURL   string               `json:"review_comments_url,omitempty"`
	ReviewCommentURL    string               `json:"review_comment_url,omitempty"`
	ReviewComments      int                  `json:"review_comments,omitempty"`
	Assignee            User                 `json:"assignee,omitempty"`
	Assignees           []User               `json:"assignees,omitempty"`
	MaintainerCanModify bool                 `json:"maintainer_can_modify,omitempty"`
	AuthorAssociation   string               `json:"author_association,omitempty"`
	RequestedReviewers  []User               `json:"requested_reviewers,omitempty"`
	AutoMerge           PullRequestAutoMerge `json:"auto_merge,omitempty"`
	Head                PullRequestBranch    `json:"head,omitempty"`
	Base                PullRequestBranch    `json:"base,omitempty"`
}

type UpdatePullRequest struct {
	Title string `json:"title,omitempty"`
	Body  string `json:"body,omitempty"`
	State string `json:"state,omitempty"`
	Base  string `json:"base,omitempty"`
}

type NewPullRequest struct {
	Title               string `json:"title,omitempty"`
	Head                string `json:"head,omitempty"`
	Base                string `json:"base,omitempty"`
	Body                string `json:"body,omitempty"`
	Issue               int    `json:"issue,omitempty"`
	MaintainerCanModify bool   `json:"maintainer_can_modify,omitempty"`
	Draft               bool   `json:"draft,omitempty"`
}

// PullRequestComment represents a comment left on a pull request.
type PullRequestComment struct {
	ID                  int64     `json:"id,omitempty"`
	NodeID              string    `json:"node_id,omitempty"`
	InReplyTo           int64     `json:"in_reply_to_id,omitempty"`
	Body                string    `json:"body,omitempty"`
	Path                string    `json:"path,omitempty"`
	DiffHunk            string    `json:"diff_hunk,omitempty"`
	PullRequestReviewID int64     `json:"pull_request_review_id,omitempty"`
	Position            int       `json:"position,omitempty"`
	OriginalPosition    int       `json:"original_position,omitempty"`
	StartLine           int       `json:"start_line,omitempty"`
	Line                int       `json:"line,omitempty"`
	OriginalLine        int       `json:"original_line,omitempty"`
	OriginalStartLine   int       `json:"original_start_line,omitempty"`
	Side                string    `json:"side,omitempty"`
	StartSide           string    `json:"start_side,omitempty"`
	CommitID            string    `json:"commit_id,omitempty"`
	OriginalCommitID    string    `json:"original_commit_id,omitempty"`
	User                *User     `json:"user,omitempty"`
	CreatedAt           time.Time `json:"created_at,omitempty"`
	UpdatedAt           time.Time `json:"updated_at,omitempty"`
	// AuthorAssociation is the comment author's relationship to the pull request's repository.
	// Possible values are "COLLABORATOR", "CONTRIBUTOR", "FIRST_TIMER", "FIRST_TIME_CONTRIBUTOR", "MEMBER", "OWNER", or "NONE".
	AuthorAssociation string `json:"author_association,omitempty"`
	URL               string `json:"url,omitempty"`
	HTMLURL           string `json:"html_url,omitempty"`
	PullRequestURL    string `json:"pull_request_url,omitempty"`
}
