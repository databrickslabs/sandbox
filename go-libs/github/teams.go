package github

type Team struct {
	ID          int64  `json:"id,omitempty"`
	NodeID      string `json:"node_id,omitempty"`
	Name        string `json:"name,omitempty"`
	Description string `json:"description,omitempty"`
	URL         string `json:"url,omitempty"`
	Slug        string `json:"slug,omitempty"`

	// Permission specifies the default permission for repositories owned by the team.
	Permission string `json:"permission,omitempty"`

	// Permissions identifies the permissions that a team has on a given
	// repository. This is only populated when calling Repositories.ListTeams.
	Permissions map[string]bool `json:"permissions,omitempty"`

	// Privacy identifies the level of privacy this team should have.
	// Possible values are:
	//     secret - only visible to organization owners and members of this team
	//     closed - visible to all members of this organization
	// Default is "secret".
	Privacy string `json:"privacy,omitempty"`

	MembersCount    *int   `json:"members_count,omitempty"`
	ReposCount      *int   `json:"repos_count,omitempty"`
	HTMLURL         string `json:"html_url,omitempty"`
	MembersURL      string `json:"members_url,omitempty"`
	RepositoriesURL string `json:"repositories_url,omitempty"`
	Parent          *Team  `json:"parent,omitempty"`
}

type NewTeam struct {
	Name         string   `json:"name"`
	Description  string   `json:"description,omitempty"`
	Maintainers  []string `json:"maintainers,omitempty"`
	RepoNames    []string `json:"repo_names,omitempty"`
	ParentTeamID int64    `json:"parent_team_id,omitempty"`

	// Privacy identifies the level of privacy this team should have.
	// Possible values are:
	//     secret - only visible to organization owners and members of this team
	//     closed - visible to all members of this organization
	// Default is "secret".
	Privacy string `json:"privacy,omitempty"`
}
