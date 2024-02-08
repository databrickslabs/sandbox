package testenv

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"time"

	"github.com/databricks/databricks-sdk-go/apierr"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/env"
)

type loadedEnv struct {
	v     *vaultEnv
	mpath string
	vars  map[string]string
}

func (l *loadedEnv) getDatabricksConfig() (*config.Config, error) {
	cfg := &config.Config{}
	// TODO: add output redaction for secrets based on sensitive values
	for _, a := range config.ConfigAttributes {
		for _, ev := range a.EnvVars {
			v, ok := l.vars[ev]
			if !ok {
				continue
			}
			err := a.SetS(cfg, v)
			if err != nil {
				return nil, fmt.Errorf("set %s: %w", a.Name, err)
			}
		}
	}
	return cfg, cfg.EnsureResolved()
}

func (l *loadedEnv) Start(ctx context.Context) (context.Context, error) {
	cfg, err := l.getDatabricksConfig()
	if err != nil {
		return nil, fmt.Errorf("config: %w", err)
	}
	srv := l.metadataServer(cfg)
	authVars := map[string]bool{}
	for _, a := range config.ConfigAttributes {
		if a.Auth == "" {
			continue
		}
		for _, ev := range a.EnvVars {
			authVars[ev] = true
		}
	}
	ctx = env.Set(ctx, "CLOUD_ENV", strings.ToLower(string(cfg.Environment().Cloud)))
	ctx = env.Set(ctx, "DATABRICKS_METADATA_SERVICE_URL", fmt.Sprintf("%s/%s", srv, l.mpath))
	for k, v := range l.vars {
		if authVars[k] {
			continue
		}
		ctx = env.Set(ctx, k, v)
	}
	return ctx, err
}

func (l *loadedEnv) metadataServer(cfg *config.Config) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer r.Body.Close()
		if r.Header.Get("X-Databricks-Metadata-Version") != "1" {
			l.replyJson(r.Context(), w, 400, apierr.APIErrorBody{
				ErrorCode: "BAD_REQUEST",
				Message:   "Version mismatch",
			})
			return
		}
		if r.URL.Path != l.mpath {
			l.replyJson(r.Context(), w, 404, apierr.APIErrorBody{
				ErrorCode: "NOT_FOUND",
				Message:   "nope",
			})
			return
		}
		if r.Header.Get("X-Databricks-Host") != cfg.Host {
			l.replyJson(r.Context(), w, 403, apierr.APIErrorBody{
				ErrorCode: "PERMISSION_DENIED",
				Message:   "Host mismatch",
			})
			return
		}
		req := &http.Request{Header: http.Header{}}
		err := cfg.Authenticate(req)
		if err != nil {
			l.replyJson(r.Context(), w, 403, apierr.APIErrorBody{
				ErrorCode: "PERMISSION_DENIED",
				Message:   err.Error(),
			})
			return
		}
		tokenType, accessToken, ok := strings.Cut(req.Header.Get("Authorization"), " ")
		if !ok {
			l.replyJson(r.Context(), w, 400, apierr.APIErrorBody{
				ErrorCode: "BAD_REQUEST",
				Message:   "Wrong Authorization header",
			})
		}
		l.replyJson(r.Context(), w, 200, msiToken{
			TokenType:   tokenType,
			AccessToken: accessToken,
			// for the sake of simplicity, we always expire tokens within 2 minutes
			ExpiresOn: json.Number(fmt.Sprint(time.Now().Add(2 * time.Minute).Unix())),
		})
	}))
}

func (l *loadedEnv) replyJson(ctx context.Context, w http.ResponseWriter, status int, body any) {
	raw, err := json.Marshal(body)
	if err != nil {
		logger.Errorf(ctx, "json write: %s", err)
		w.WriteHeader(500)
		return
	}
	w.WriteHeader(status)
	w.Write(raw)
}
