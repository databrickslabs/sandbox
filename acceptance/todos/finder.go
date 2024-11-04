package todos

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/git"
	"github.com/databrickslabs/sandbox/go-libs/github"
)

func New(ctx context.Context, gh *github.GitHubClient, root string) (*TechnicalDebtFinder, error) {
	fs, err := fileset.RecursiveChildren(root)
	if err != nil {
		return nil, fmt.Errorf("fileset: %w", err)
	}
	raw, err := os.ReadFile(filepath.Join(root, ".gitignore"))
	if err != nil {
		return nil, fmt.Errorf("read .gitignore: %w", err)
	}
	ignorer := newIncluder(append(strings.Split(string(raw), "\n"), ".git/", "*.gif", "*.png"))
	var scope fileset.FileSet
	for _, file := range fs {
		include, _ := ignorer.IgnoreFile(file.Relative)
		if !include {
			continue
		}
		scope = append(scope, file)
	}
	checkout, err := git.NewCheckout(ctx, root)
	if err != nil {
		return nil, fmt.Errorf("git: %w", err)
	}
	return &TechnicalDebtFinder{
		fs:  scope,
		git: checkout,
		gh:  gh,
	}, nil
}

type TechnicalDebtFinder struct {
	fs  fileset.FileSet
	git *git.Checkout
	gh  *github.GitHubClient
}

type Todo struct {
	message string
	link    string
}

func (f *TechnicalDebtFinder) CreateIssues(ctx context.Context) error {
	todos, err := f.allTodos(ctx)
	if err != nil {
		return fmt.Errorf("all todos: %w", err)
	}
	seen, err := f.seenIssues(ctx)
	if err != nil {
		return fmt.Errorf("seen issues: %w", err)
	}
	for _, todo := range todos {
		if seen[todo.message] {
			continue
		}
		if err := f.createIssue(ctx, todo); err != nil {
			return fmt.Errorf("create issue: %w", err)
		}
	}
	return nil
}

func (f *TechnicalDebtFinder) createIssue(ctx context.Context, todo Todo) error {
	org, repo, ok := f.git.OrgAndRepo()
	if !ok {
		return fmt.Errorf("git org and repo")
	}
	_, err := f.gh.CreateIssue(ctx, org, repo, github.NewIssue{
		Title:  fmt.Sprintf("[TODO] %s", todo.message),
		Body:   fmt.Sprintf("See: %s", todo.link),
		Labels: []string{"tech debt"},
	})
	if err != nil {
		return fmt.Errorf("create issue: %w", err)
	}
	return nil
}

func (f *TechnicalDebtFinder) seenIssues(ctx context.Context) (map[string]bool, error) {
	org, repo, ok := f.git.OrgAndRepo()
	if !ok {
		return nil, fmt.Errorf("git org and repo")
	}
	seen := map[string]bool{}
	it := f.gh.ListRepositoryIssues(ctx, org, repo, &github.ListIssues{
		State:  "all",
		Labels: []string{"tech debt"},
	})
	for it.HasNext(ctx) {
		issue, err := it.Next(ctx)
		if err != nil {
			return nil, fmt.Errorf("next: %w", err)
		}
		if !strings.HasPrefix(issue.Title, "[TODO] ") {
			continue
		}
		norm := strings.TrimPrefix(issue.Title, "[TODO] ")
		seen[norm] = true
	}
	return seen, nil
}

func (f *TechnicalDebtFinder) allTodos(ctx context.Context) ([]Todo, error) {
	prefix, err := f.embedPrefix(ctx)
	if err != nil {
		return nil, fmt.Errorf("prefix: %w", err)
	}
	var todos []Todo
	needle := regexp.MustCompile(`TODO:(.*)`)
	for _, v := range f.fs {
		raw, err := v.Raw()
		if err != nil {
			return nil, fmt.Errorf("%s: %w", v.Relative, err)
		}
		lines := strings.Split(string(raw), "\n")
		for i, line := range lines {
			if !needle.MatchString(line) {
				continue
			}
			todos = append(todos, Todo{
				message: strings.TrimSpace(needle.FindStringSubmatch(line)[1]),
				link:    fmt.Sprintf("%s/%s#L%d-L%d", prefix, v.Relative, i, i+5),
			})
		}
	}
	return todos, nil
}

func (f *TechnicalDebtFinder) embedPrefix(ctx context.Context) (string, error) {
	org, repo, ok := f.git.OrgAndRepo()
	if !ok {
		return "", fmt.Errorf("git org and repo")
	}
	commits, err := f.git.History(ctx)
	if err != nil {
		return "", fmt.Errorf("git history: %w", err)
	}
	// example: https://github.com/databrickslabs/ucx/blob/69a0cf8ce3450680dc222150f500d84a1eb523fc/src/databricks/labs/ucx/azure/access.py#L25-L35
	prefix := fmt.Sprintf("https://github.com/%s/%s/blame/%s", org, repo, commits[0].Sha)
	return prefix, nil
}
