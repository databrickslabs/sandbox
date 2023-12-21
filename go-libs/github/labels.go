package github

type Label struct {
	ID          int64  `json:"id,omitempty"`
	URL         string `json:"url,omitempty"`
	Name        string `json:"name,omitempty"`
	Color       string `json:"color,omitempty"`
	Description string `json:"description,omitempty"`
	Default     bool   `json:"default,omitempty"`
	NodeID      string `json:"node_id,omitempty"`
}
