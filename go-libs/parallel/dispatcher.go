package parallel

import (
	"context"
	"sync"

	"github.com/databricks/databricks-sdk-go/logger"
)

func Tasks[T, R any](ctx context.Context, workers int, tasks []T, mapper func(context.Context, T) (R, error)) ([]R, error) {
	p := &pool[T, R]{
		mapper:   mapper,
		dispatch: make(chan T),
		work:     make(chan T),
		replies:  make(chan R),
		errs:     make(chan error),
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	go p.dispatcher(ctx)
	go p.collector(ctx)
	go p.killSwitch(ctx, cancel)
	for i := 0; i < workers; i++ {
		go p.worker(ctx)
	}
	for _, t := range tasks {
		p.wg.Add(1)
		select {
		case <-ctx.Done():
			return nil, p.lastErr
		case p.dispatch <- t:
		}
	}
	p.wg.Wait()
	return p.chunks, p.lastErr
}

type pool[T, R any] struct {
	mapper   func(context.Context, T) (R, error)
	dispatch chan T
	work     chan T
	replies  chan R
	errs     chan error
	chunks   []R
	lastErr  error
	wg       sync.WaitGroup
}

func (p *pool[T, R]) dispatcher(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case t := <-p.dispatch:
			p.work <- t
		}
	}
}

func (p *pool[T, R]) killSwitch(ctx context.Context, cancel func()) {
	for {
		select {
		case <-ctx.Done():
			return
		case err := <-p.errs:
			logger.Errorf(ctx, err.Error())
			p.lastErr = err
			p.wg.Done()
			cancel()
			return
		}
	}
}

func (p *pool[T, R]) collector(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case msg := <-p.replies:
			p.chunks = append(p.chunks, msg)
			p.wg.Done()
		}
	}
}

func (p *pool[T, R]) worker(ctx context.Context) {
	logger.Debugf(ctx, "Starting worker")
	for {
		select {
		case <-ctx.Done():
			return
		case task := <-p.work:
			result, err := p.mapper(ctx, task)
			if err != nil {
				select {
				case <-ctx.Done():
					return
				case p.errs <- err:
					continue
				}
			}
			select {
			case <-ctx.Done():
				return
			case p.replies <- result:
			}
		}
	}
}
