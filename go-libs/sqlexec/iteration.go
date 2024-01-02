package sqlexec

import (
	"context"
	"encoding/json"
	"sync"

	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databricks/databricks-sdk-go/service/sql"
)

type stringArrayIterator struct {
	result *sql.ResultData
	api    *sql.StatementExecutionAPI
	id     string
	pos    int
	err    error
	mu     sync.Mutex
}

// HasNext returns true if there are more items to iterate over. HasNext
// will also return true if the iterator needs to fetch the next page of
// items from the underlying source and the request fails, even if there
// are no more items to iterate over. In this case, Next will return the
// error.
func (i *stringArrayIterator) HasNext(ctx context.Context) bool {
	i.mu.Lock()
	defer i.mu.Unlock()
	if i.pos < len(i.result.DataArray) {
		return true
	}
	if i.result.NextChunkIndex == 0 {
		return false
	}
	i.result, i.err = i.api.GetStatementResultChunkNByStatementIdAndChunkIndex(ctx, i.id, i.result.NextChunkIndex)
	if i.err != nil {
		return false
	}
	i.pos = 0
	return true
}

// Next returns the next item in the iterator. If there are no more items
// to iterate over, it returns ErrNoMoreItems. If there was an error
// fetching the next page of items, it returns that error. Once Next
// returns ErrNoMoreItems or an error, it will continue to return that
// error.
func (i *stringArrayIterator) Next(context.Context) ([]string, error) {
	i.mu.Lock()
	defer i.mu.Unlock()
	if i.err != nil {
		return nil, i.err
	}
	row := i.result.DataArray[i.pos]
	i.pos++
	return row, nil
}

type scanIterator struct {
	ctx    context.Context
	schema *sql.ResultSchema
	sai    *stringArrayIterator
}

func (i *scanIterator) Scan(out ...any) bool {
	if len(out) == 0 {
		logger.Errorf(i.ctx, "empty arguments")
		return false
	}
	if !i.sai.HasNext(i.ctx) {
		return false
	}
	row, err := i.sai.Next(i.ctx)
	if err != nil {
		logger.Errorf(i.ctx, "failed to fetch: %w", err)
		return false
	}
	for j := 0; j < len(out); j++ {
		err := i.unmarshall(i.schema.Columns[j].TypeName, row[j], &out[j])
		if err != nil {
			logger.Errorf(i.ctx, "failed to fetch: %s", err)
			i.sai.err = err
			return false
		}
	}
	return true
}

func (i *scanIterator) unmarshall(t sql.ColumnInfoTypeName, in string, out any) error {
	err := json.Unmarshal([]byte(in), out)
	if err != nil {
		return err
	}
	return nil
}

type iterableResult struct {
	scanner  *scanIterator
	iterator listing.Iterator[[]string]
}

// Scan mimics the rows interface from go - see https://pkg.go.dev/database/sql#example-Rows
func (rc *iterableResult) Scan(out ...any) bool {
	return rc.scanner.Scan(out...)
}

func (rc *iterableResult) Err() error {
	return rc.scanner.sai.err
}

func (rc *iterableResult) HasNext(ctx context.Context) bool {
	return rc.iterator.HasNext(ctx)
}

func (rc *iterableResult) Next(ctx context.Context) ([]string, error) {
	return rc.iterator.Next(ctx)
}
