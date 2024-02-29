package llnotes

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"sync"

	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/github"
	"github.com/databrickslabs/sandbox/go-libs/sed"
)

const blogPrompt = `SYSTEM:
You are professional technical writer and you receive draft release notes for %s of project called %s in a markdown format from multiple team members. 
Project can be described as "%s"

You write a long post announcement that takes 5 minutes to read, summarize the most important features, and mention them on top. Keep the markdown links when relevant.
Do not use headings. Write fluent paragraphs, that are at least few sentences long. Blog post title should nicely summarize the feature increments of this release.

Don't abuse lists. paragraphs should have at least 3-4 sentences. The title should be one-sentence summary of the incremental updates for this release

You aim at driving more adoption of the project on Medium.

USER:
`

func (lln *llNotes) ReleaseNotes(ctx context.Context, newVersion string) (History, error) {
	versions, err := listing.ToSlice(ctx, lln.gh.Versions(ctx, lln.org, lln.repo))
	if err != nil {
		return nil, fmt.Errorf("versions: %w", err)
	}
	repo, err := lln.gh.GetRepo(ctx, lln.org, lln.repo)
	if err != nil {
		return nil, fmt.Errorf("get repo: %w", err)
	}
	latestTag := "v0.0.0" // special value for first-release projects
	if len(versions) > 0 {
		latestTag = versions[0].Version
	}
	pool := &summarizePool{
		lln:      lln,
		dispatch: make(chan github.RepositoryCommit),
		work:     make(chan github.RepositoryCommit),
		errs:     make(chan error),
		results:  make(chan string),
	}
	ctx, cancel := pool.start(ctx)
	defer cancel()
	commits := lln.gh.CompareCommits(ctx, lln.org, lln.repo, latestTag, repo.DefaultBranch)
	for commits.HasNext(ctx) {
		commit, err := commits.Next(ctx)
		if err != nil {
			return nil, fmt.Errorf("commit: %w", err)
		}
		pool.wg.Add(1)
		select {
		case <-ctx.Done():
			return nil, pool.lastErr
		case pool.dispatch <- commit:
		}
	}
	pool.wg.Wait()
	sort.Strings(pool.notes)
	rawNotes := strings.Join(pool.notes, "\n")
	logger.Debugf(ctx, "Raw notes: %s", rawNotes)
	return lln.Talk(ctx, History{
		SystemMessage(fmt.Sprintf(blogPrompt, newVersion, repo.Name, repo.Description)),
		UserMessage(rawNotes),
	})
}

type summarizePool struct {
	lln      *llNotes
	dispatch chan github.RepositoryCommit
	work     chan github.RepositoryCommit
	results  chan string
	errs     chan error
	lastErr  error
	wg       sync.WaitGroup
	notes    []string
}

func (s *summarizePool) start(ctx context.Context) (context.Context, func()) {
	ctx, cancel := context.WithCancel(ctx)
	go s.dispatcher(ctx, cancel)
	for i := 0; i < 5; i++ {
		go s.worker(ctx)
	}
	return ctx, cancel
}

func (s *summarizePool) dispatcher(ctx context.Context, cancel func()) {
	for {
		select {
		case <-ctx.Done():
			return
		case t := <-s.dispatch:
			s.work <- t
		case msg := <-s.results:
			s.notes = append(s.notes, msg)
			s.wg.Done()
		case err := <-s.errs:
			logger.Errorf(ctx, err.Error())
			s.lastErr = err
			cancel()
			return
		}
	}
}

var cleanup = sed.Pipeline{
	sed.Rule("Add ", "Added "),
	sed.Rule("Adding ", "Added "),
	sed.Rule("Change ", "Changed "),
	sed.Rule("Enable ", "Enabled "),
	sed.Rule("Handle ", "Added handling for "),
	sed.Rule("Enforce ", "Enforced "),
	sed.Rule("Migrate ", "Added migration for "),
	sed.Rule("Fix ", "Fixed "),
	sed.Rule("Move ", "Moved "),
	sed.Rule("Update ", "Updated "),
	sed.Rule("Remove ", "Removed "),
	sed.Rule(`\. \(`, ` (`),
}

func (s *summarizePool) worker(ctx context.Context) {
	logger.Debugf(ctx, "Starting worker")
	for {
		select {
		case <-ctx.Done():
			return
		case commit := <-s.work:
			logger.Debugf(ctx, "Working on task")
			history, err := s.lln.Commit(ctx, &commit)
			if err != nil {
				s.errs <- fmt.Errorf("explain: %w", err)
				continue
			}
			short := cleanup.Apply(strings.Split(commit.Commit.Message, "\n")[0])
			message := s.lln.norm.Apply(history.Last())
			s.results <- fmt.Sprintf(" * %s. %s", short, message)
		}
	}
}
