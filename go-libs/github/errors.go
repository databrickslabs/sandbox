package github

import (
	"errors"
	"fmt"
	"time"

	"github.com/databricks/databricks-sdk-go/httpclient"
)

var (
	ErrBadRequest             = errors.New("the request is invalid")
	ErrUnauthenticated        = errors.New("the request does not have valid authentication (AuthN) credentials for the operation")
	ErrPermissionDenied       = errors.New("the caller does not have permission to execute the specified operation")
	ErrNotFound               = errors.New("the operation was performed on a resource that does not exist")
	ErrResourceConflict       = errors.New("maps to all HTTP 409 (Conflict) responses")
	ErrTooManyRequests        = errors.New("maps to HTTP code: 429 Too Many Requests")
	ErrCancelled              = errors.New("the operation was explicitly canceled by the caller")
	ErrInternalError          = errors.New("some invariants expected by the underlying system have been broken")
	ErrNotImplemented         = errors.New("the operation is not implemented or is not supported/enabled in this service")
	ErrTemporarilyUnavailable = errors.New("the service is currently unavailable")
	ErrDeadlineExceeded       = errors.New("the deadline expired before the operation could complete")

	statusCodeMapping = map[int]error{
		400: ErrBadRequest,
		401: ErrUnauthenticated,
		403: ErrPermissionDenied,
		404: ErrNotFound,
		409: ErrResourceConflict,
		429: ErrTooManyRequests,
		499: ErrCancelled,
		500: ErrInternalError,
		501: ErrNotImplemented,
		503: ErrTemporarilyUnavailable,
		504: ErrDeadlineExceeded,
	}
)

type Error struct {
	*httpclient.HttpError
	Message            string `json:"message"`
	DocumentationURL   string `json:"documentation_url"`
	retryAfter         time.Duration
	rateLimitReset     time.Time
	rateLimitRemaining int
}

func (err *Error) Error() string {
	return fmt.Sprintf("%s. See %s", err.Message, err.DocumentationURL)
}

// Unwrap error for easier client code checking
//
// See https://pkg.go.dev/errors#example-Unwrap
func (err *Error) Unwrap() []error {
	byStatusCode, ok := statusCodeMapping[err.StatusCode]
	if ok {
		return []error{byStatusCode, err.HttpError}
	}
	// A nil error returned from e.Unwrap() indicates that e does not wrap
	// any error.
	return []error{err.HttpError}
}
