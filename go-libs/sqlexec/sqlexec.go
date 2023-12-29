package sqlexec

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"strings"
	"sync"
	"time"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/apierr"
	"github.com/databricks/databricks-sdk-go/client"
	"github.com/databricks/databricks-sdk-go/listing"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databricks/databricks-sdk-go/service/sql"
)

// NewStatementExecutionExt creates a new StatementExecutionExt instance
func NewStatementExecutionExt(w *databricks.WorkspaceClient) (*StatementExecutionExt, error) {
	client, err := client.New(w.Config)
	if err != nil {
		return nil, err
	}
	return &StatementExecutionExt{
		client:                client,
		StatementExecutionAPI: w.StatementExecution,
	}, nil
}

// StatementExecutionExt represents the extended statement execution API
type StatementExecutionExt struct {
	*sql.StatementExecutionAPI
	client *client.DatabricksClient
}

// Constants
const (
	MaxSleepPerAttempt = 10
	MaxPlatformTimeout = 50
	MinPlatformTimeout = 5
	DefaultWaitTimeout = 20 * time.Minute
)

// raiseIfNeeded raises an error if the statement execution status indicates an error
func (s *StatementExecutionExt) raiseIfNeeded(status *sql.StatementStatus) error {
	if status.State != sql.StatementStateFailed && status.State != sql.StatementStateCanceled && status.State != sql.StatementStateClosed {
		return nil
	}
	statusError := status.Error
	if statusError == nil {
		statusError = &sql.ServiceError{Message: "unknown", ErrorCode: sql.ServiceErrorCodeUnknown}
	}
	errorMessage := statusError.Message
	if errorMessage == "" {
		errorMessage = "unknown error"
	}
	if strings.Contains(errorMessage, "SCHEMA_NOT_FOUND") {
		return fmt.Errorf("%s. %w", errorMessage, apierr.ErrNotFound)
	}
	if strings.Contains(errorMessage, "TABLE_OR_VIEW_NOT_FOUND") {
		return fmt.Errorf("%s. %w", errorMessage, apierr.ErrNotFound)
	}
	// TODO: error mapping
	return fmt.Errorf(errorMessage)
}

// Execute executes a SQL statement and returns the execution response
func (s *StatementExecutionExt) Execute(ctx context.Context, warehouseID string, statement string, byteLimit int, catalog string, schema string, timeout time.Duration) (*sql.ExecuteStatementResponse, error) {
	waitTimeout := ""
	// if MinPlatformTimeout <= timeout.Seconds() && timeout.Seconds() <= MaxPlatformTimeout {
	// 	waitTimeout = fmt.Sprintf("%fs", timeout.Seconds())
	// }
	logger.Infof(ctx, "Executing SQL statement: %s\n", statement)
	immediateResponse, err := s.ExecuteStatement(ctx, sql.ExecuteStatementRequest{
		WarehouseId: warehouseID,
		Statement:   statement,
		Catalog:     catalog,
		Schema:      schema,
		Disposition: sql.DispositionInline,
		Format:      sql.FormatJsonArray,
		ByteLimit:   int64(byteLimit),
		WaitTimeout: waitTimeout,
	})
	if err != nil {
		return nil, err
	}
	status := immediateResponse.Status
	if status == nil {
		status = &sql.StatementStatus{State: sql.StatementStateFailed}
	}
	if status.State == sql.StatementStateSucceeded {
		return immediateResponse, nil
	}
	if err := s.raiseIfNeeded(status); err != nil {
		return nil, err
	}
	attempt := 1
	statusMessage := "polling..."
	deadline := time.Now().Add(timeout)
	statementID := immediateResponse.StatementId
	for time.Now().Before(deadline) {
		res, err := s.GetStatementByStatementId(ctx, statementID)
		if err != nil {
			return nil, err
		}
		resultStatus := res.Status
		if resultStatus == nil {
			return nil, fmt.Errorf("Result status is nil: %v", res)
		}
		state := resultStatus.State
		if state == "" {
			state = sql.StatementStateFailed
		}
		if state == sql.StatementStateSucceeded {
			return &sql.ExecuteStatementResponse{
				Manifest:    res.Manifest,
				Result:      res.Result,
				StatementId: statementID,
				Status:      resultStatus,
			}, nil
		}
		statusMessage = fmt.Sprintf("current status: %s", state)
		if err := s.raiseIfNeeded(resultStatus); err != nil {
			return nil, err
		}
		sleep := time.Duration(attempt)
		if sleep > MaxSleepPerAttempt {
			// sleep 10s max per attempt
			sleep = MaxSleepPerAttempt
		}
		log.Printf("SQL statement %s: %s (sleeping ~%ds)\n", statementID, statusMessage, int(sleep.Seconds()))
		time.Sleep(sleep + time.Duration(rand.Float64()))
		attempt++
	}
	err = s.CancelExecution(ctx, sql.CancelExecutionRequest{
		StatementId: statementID,
	})
	if err != nil {
		return nil, err
	}
	msg := fmt.Sprintf("timed out after %s: %s", timeout, statusMessage)
	return nil, fmt.Errorf(msg)
}

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
	return i.result.DataArray[i.pos], nil
}

type niceIterator struct {
	ctx    context.Context
	schema *sql.ResultSchema
	sai    *stringArrayIterator
}

func (i *niceIterator) Next(out ...any) bool {
	if !i.sai.HasNext(i.ctx) {
		return false
	}
	row, err := i.sai.Next(i.ctx)
	if err != nil {
		logger.Errorf(i.ctx, "failed to fetch: %w", err)
		return false
	}
	for j := 0; j < len(out); j++ {
		err := i.x(i.schema.Columns[j].TypeName, row[j], &out[j])
		if err != nil {
			logger.Errorf(i.ctx, "failed to fetch: %w", err)
			return false
		}
	}
	return true
}

func (i *niceIterator) x(t sql.ColumnInfoTypeName, in string, out any) error {
	var tmp string
	err := json.Unmarshal([]byte(in), &tmp)
	if err != nil {
		return err
	}
	err = json.Unmarshal([]byte(tmp), &out)
	if err != nil {
		return err
	}
	return nil
}

type rowConsumer struct {
	Nice        *niceIterator
	StringSlice listing.Iterator[[]string]
}

// ExecuteFetchAll executes a SQL statement and returns an iterator of rows
func (s *StatementExecutionExt) ExecuteFetchAll(ctx context.Context, warehouseID string, statement string, byteLimit int, catalog string, schema string, timeout time.Duration) (*rowConsumer, error) {
	executeResponse, err := s.Execute(ctx, warehouseID, statement, byteLimit, catalog, schema, timeout)
	if err != nil {
		return nil, err
	}
	manifest := executeResponse.Manifest
	if manifest == nil {
		return nil, fmt.Errorf("missing manifest: %v", executeResponse)
	}
	manifestSchema := manifest.Schema
	if manifestSchema == nil {
		return nil, fmt.Errorf("missing schema: %v", manifest)
	}
	sai := &stringArrayIterator{
		id:     executeResponse.StatementId,
		result: executeResponse.Result,
		api:    s.StatementExecutionAPI,
	}
	return &rowConsumer{
		StringSlice: sai,
		Nice: &niceIterator{
			schema: manifest.Schema,
			ctx:    ctx,
			sai:    sai,
		},
	}, nil
}
