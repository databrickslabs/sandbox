package internal

import (
	"context"
	"path/filepath"
	"runtime"
	"sync"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/git"
	"github.com/databrickslabs/sandbox/go-libs/github"
)

type globalInfo struct {
	cacheDir string
	github   *github.GitHubClient
	tasks    chan cloneRepo
	reply    chan *Clone
	errs     chan error
	failure  error
	wg       sync.WaitGroup
	clones   Clones
}

type cloneRepo struct {
	github.Repo
	Item
}

func NewGlobalInfo(cacheDir string, cfg *github.GitHubConfig) *globalInfo {
	return &globalInfo{
		cacheDir: cacheDir,
		github:   github.NewClient(cfg),
		tasks:    make(chan cloneRepo),
		reply:    make(chan *Clone),
		errs:     make(chan error),
	}
}

func (g *globalInfo) Checkout(ctx context.Context) (Clones, error) {
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	go g.dispatcher(ctx, cancel)
	for i := 0; i < runtime.NumCPU()*2; i++ {
		go g.worker(ctx)
	}
	for _, v := range inventory {
		switch {
		case v.Repo != "":
			repo, err := g.github.GetRepo(ctx, v.Org, v.Repo)
			if err != nil {
				return nil, err
			}
			g.wg.Add(1)
			g.tasks <- cloneRepo{repo, v}
			continue
		case v.Org != "":
			repos, err := g.github.ListRepositories(ctx, v.Org)
			if err != nil {
				return nil, err
			}
			for _, repo := range repos {
				if repo.IsArchived {
					logger.Debugf(ctx, "Skipping archived repo: %s", repo.Name)
					continue
				}
				g.wg.Add(1)
				g.tasks <- cloneRepo{repo, v}
				continue
			}
		}
	}
	g.wg.Wait()
	return g.clones, g.failure
}

func (g *globalInfo) dispatcher(ctx context.Context, cancel func()) {
	// we need a single dispatcher to govern all replies from workers,
	// otherwise workers will be blocked on others
	for {
		select {
		case <-ctx.Done():
			return
		case clone := <-g.reply:
			g.clones = append(g.clones, clone)
			g.wg.Done()
			continue
		case err := <-g.errs:
			g.failure = err
			cancel()
			return
		}
	}
}

func (g *globalInfo) worker(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case task := <-g.tasks:
			clone, err := g.clone(ctx, task.Item, task.Repo)
			if err != nil {
				g.errs <- err
				continue
			}
			g.reply <- clone
		}
	}
}

func (g *globalInfo) clone(ctx context.Context, v Item, repo github.Repo) (*Clone, error) {
	dir := filepath.Join(g.cacheDir, v.Org, repo.Name)
	checkout, err := git.LazyClone(ctx, repo.SshURL, dir)
	if err != nil {
		return nil, err
	}
	fs, err := fileset.RecursiveChildren(dir)
	if err != nil {
		return nil, err
	}
	return &Clone{
		Inventory: v,
		Repo:      repo,
		Git:       checkout,
		FileSet:   fs,
	}, nil
}
