package sqlexec

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"sync"
	"time"

	"github.com/databricks/databricks-sdk-go"
	"github.com/databricks/databricks-sdk-go/apierr"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databricks/databricks-sdk-go/service/sql"
)

const (
	maxSleepPerAttempt = 10
	maxPlatformTimeout = 50
	minPlatformTimeout = 5
	defaultWaitTimeout = 20 * time.Minute
)

// New creates a new StatementExecutionExt instance
func New(w *databricks.WorkspaceClient) (*StatementExecutionExt, error) {
	return &StatementExecutionExt{
		statementExecutionAPI: w.StatementExecution,
		warehousesAPI:         w.Warehouses,
		warehouseID:           w.Config.WarehouseID,
	}, nil
}

// StatementExecutionExt represents the extended statement execution API
type StatementExecutionExt struct {
	statementExecutionAPI *sql.StatementExecutionAPI
	warehousesAPI         *sql.WarehousesAPI
	warehouseID           string
	mu                    sync.Mutex
}

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
	if strings.Contains(errorMessage, "PATH_NOT_FOUND") {
		return fmt.Errorf("%s. %w", errorMessage, apierr.ErrNotFound)
	}
	if strings.Contains(errorMessage, "already exists") {
		return fmt.Errorf("%s. %w", errorMessage, apierr.ErrAlreadyExists)
	}
	errorMapping := map[sql.ServiceErrorCode]error{
		sql.ServiceErrorCodeAborted:                apierr.ErrAborted,
		sql.ServiceErrorCodeAlreadyExists:          apierr.ErrAlreadyExists,
		sql.ServiceErrorCodeBadRequest:             apierr.ErrBadRequest,
		sql.ServiceErrorCodeCancelled:              apierr.ErrCancelled,
		sql.ServiceErrorCodeDeadlineExceeded:       apierr.ErrDeadlineExceeded,
		sql.ServiceErrorCodeInternalError:          apierr.ErrInternalError,
		sql.ServiceErrorCodeNotFound:               apierr.ErrNotFound,
		sql.ServiceErrorCodeUnauthenticated:        apierr.ErrUnauthenticated,
		sql.ServiceErrorCodeUnknown:                apierr.ErrUnknown,
		sql.ServiceErrorCodeTemporarilyUnavailable: apierr.ErrTemporarilyUnavailable,
	}
	found, ok := errorMapping[statusError.ErrorCode]
	if ok {
		return found
	}
	return fmt.Errorf(errorMessage)
}

type ExecuteStatement struct {
	WarehouseID string
	Statement   string
	Catalog     string
	Schema      string
	Timeout     time.Duration
	Disposition sql.Disposition
}

func (s *StatementExecutionExt) determineDefaultWarehouse(ctx context.Context) (string, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.warehouseID != "" {
		return s.warehouseID, nil
	}
	warehouses, err := s.warehousesAPI.ListAll(ctx, sql.ListWarehousesRequest{})
	if err != nil {
		return "", fmt.Errorf("list warehouses: %w", err)
	}
	ids := []string{}
	for _, v := range warehouses {
		switch v.State {
		case sql.StateDeleted, sql.StateDeleting:
			continue
		case sql.StateRunning:
			// first running warehouse
			s.warehouseID = v.Id
			return s.warehouseID, nil
		default:
			ids = append(ids, v.Id)
		}
	}
	if s.warehouseID == "" && len(ids) > 0 {
		// otherwise first warehouse
		s.warehouseID = ids[0]
		return s.warehouseID, nil
	}
	return "", fmt.Errorf("no warehouse id given")
}

// executeAndWait executes a SQL statement and returns the execution response
func (s *StatementExecutionExt) executeAndWait(ctx context.Context, req ExecuteStatement) (*sql.ExecuteStatementResponse, error) {
	if req.WarehouseID == "" {
		req.WarehouseID = s.warehouseID
	}
	if req.WarehouseID == "" {
		warehouseID, err := s.determineDefaultWarehouse(ctx)
		if err != nil {
			return nil, fmt.Errorf("default warehouse: %w", err)
		}
		req.WarehouseID = warehouseID
	}
	if req.Timeout == 0 {
		req.Timeout = defaultWaitTimeout
	}
	waitTimeout := ""
	if minPlatformTimeout <= req.Timeout.Seconds() && req.Timeout.Seconds() <= maxPlatformTimeout {
		waitTimeout = fmt.Sprintf("%fs", req.Timeout.Seconds())
	}
	logger.Debugf(ctx, "Executing SQL statement: %s\n", req.Statement)
	immediateResponse, err := s.statementExecutionAPI.ExecuteStatement(ctx, sql.ExecuteStatementRequest{
		WarehouseId: req.WarehouseID,
		Statement:   req.Statement,
		Catalog:     req.Catalog,
		Schema:      req.Schema,
		Disposition: req.Disposition,
		Format:      sql.FormatJsonArray,
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
	deadline := time.Now().Add(req.Timeout)
	statementID := immediateResponse.StatementId
	for time.Now().Before(deadline) {
		res, err := s.statementExecutionAPI.GetStatementByStatementId(ctx, statementID)
		if err != nil {
			return nil, err
		}
		resultStatus := res.Status
		if resultStatus == nil {
			return nil, fmt.Errorf("result status is nil: %v", res)
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
		if sleep > maxSleepPerAttempt {
			// sleep 10s max per attempt
			sleep = maxSleepPerAttempt
		}
		logger.Debugf(ctx, "SQL statement %s: %s (sleeping ~%ds)",
			statementID, statusMessage, int(sleep.Seconds()))
		time.Sleep(sleep + time.Duration(rand.Float64()))
		attempt++
	}
	err = s.statementExecutionAPI.CancelExecution(ctx, sql.CancelExecutionRequest{
		StatementId: statementID,
	})
	if err != nil {
		return nil, err
	}
	return nil, fmt.Errorf("timed out after %s: %s", req.Timeout, statusMessage)
}

// Execute executes a SQL statement and returns an iterator of rows
func (s *StatementExecutionExt) Execute(ctx context.Context, req ExecuteStatement) (*iterableResult, error) {
	response, err := s.executeAndWait(ctx, req)
	if err != nil {
		return nil, err
	}
	manifest := response.Manifest
	if manifest == nil {
		return nil, fmt.Errorf("missing manifest: %v", response)
	}
	manifestSchema := manifest.Schema
	if manifestSchema == nil {
		return nil, fmt.Errorf("missing schema: %v", manifest)
	}
	sai := &stringArrayIterator{
		id:     response.StatementId,
		result: response.Result,
		api:    s.statementExecutionAPI,
	}
	return &iterableResult{
		iterator: sai,
		scanner: &scanIterator{
			schema: manifest.Schema,
			ctx:    ctx,
			sai:    sai,
		},
	}, nil
}

// Query mimics the DB.Query API - see https://pkg.go.dev/database/sql#DB.Query
func (s *StatementExecutionExt) Query(ctx context.Context, query string) (*iterableResult, error) {
	return s.Execute(ctx, ExecuteStatement{
		Statement: query,
	})
}

// Queryf is like fmt.Sprintf (AND NOT PREPARED STATEMENT). There's no SQL Injection prevention
func (s *StatementExecutionExt) Queryf(ctx context.Context, queryTemplate string, args ...any) (*iterableResult, error) {
	return s.Query(ctx, fmt.Sprintf(queryTemplate, args...))
}

// Exec mimics the DB.Exec API - https://pkg.go.dev/database/sql#DB.Exec
func (s *StatementExecutionExt) Exec(ctx context.Context, query string) error {
	_, err := s.executeAndWait(ctx, ExecuteStatement{
		Statement: query,
	})
	return err
}

// Execf is like fmt.Sprintf (AND NOT PREPARED STATEMENT). There's no SQL Injection prevention
func (s *StatementExecutionExt) Execf(ctx context.Context, queryTemplate string, args ...any) error {
	return s.Exec(ctx, fmt.Sprintf(queryTemplate, args...))
}
