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
	cfg := &config.Config{
		// ignore all environment variables
		Loaders: []config.Loader{config.ConfigFile},
	}
	// TODO: add output redaction for secrets based on sensitive values
	for _, a := range config.ConfigAttributes {
		for _, ev := range a.EnvVars {
			v, ok := l.vars[ev]
			if !ok {
				continue
			}
			if a.Sensitive && l.v.a != nil {
				// mask out sensitive value from github actions output if any
				// see https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#example-masking-and-passing-a-secret-between-jobs-or-workflows
				l.v.a.AddMask(v)
			}
			err := a.SetS(cfg, v)
			if err != nil {
				return nil, fmt.Errorf("set %s: %w", a.Name, err)
			}
		}
	}
	if cfg.IsAzure() && l.v.a != nil {
		cfg.Credentials = &ghOidc{l.v}
	}
	return cfg, cfg.EnsureResolved()
}

type ghOidc struct {
	v *vaultEnv
}

func (c *ghOidc) Name() string {
	return "github-oidc"
}

func (c *ghOidc) Configure(ctx context.Context, cfg *config.Config) (func(*http.Request) error, error) {
	ts, err := c.v.oidcTokenSource(ctx, cfg.Environment().AzureApplicationID)
	if err != nil {
		return nil, fmt.Errorf("oidc: %w", err)
	}
	return func(r *http.Request) error {
		token, err := ts.Token()
		if err != nil {
			return fmt.Errorf("token: %w", err)
		}
		token.SetAuthHeader(r)
		return nil
	}, nil
}

func (l *loadedEnv) Start(ctx context.Context) (context.Context, func(), error) {
	cfg, err := l.getDatabricksConfig()
	if err != nil {
		return nil, nil, fmt.Errorf("config: %w", err)
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
	ctx = env.Set(ctx, "DATABRICKS_METADATA_SERVICE_URL", fmt.Sprintf("%s/%s", srv.URL, l.mpath))
	ctx = env.Set(ctx, "DATABRICKS_AUTH_TYPE", "metadata-service")
	for k, v := range l.vars {
		if authVars[k] {
			// empty out the irrelevant env vars, as `env.All(ctx)` merges the map with parent env
			ctx = env.Set(ctx, k, "")
			continue
		}
		ctx = env.Set(ctx, k, v)
	}
	return ctx, srv.Close, nil
}

func (l *loadedEnv) metadataServer(cfg *config.Config) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer r.Body.Close()
		ctx := r.Context()
		logger.Debugf(ctx, "landed metadata server request")
		if r.Header.Get("X-Databricks-Metadata-Version") != "1" {
			l.replyJson(ctx, w, 400, apierr.APIErrorBody{
				ErrorCode: "BAD_REQUEST",
				Message:   "Version mismatch",
			})
			return
		}
		if strings.TrimPrefix(r.URL.Path, "/") != l.mpath {
			l.replyJson(ctx, w, 404, apierr.APIErrorBody{
				ErrorCode: "NOT_FOUND",
				Message:   "nope",
			})
			return
		}
		if r.Header.Get("X-Databricks-Host") != cfg.Host {
			l.replyJson(ctx, w, 403, apierr.APIErrorBody{
				ErrorCode: "PERMISSION_DENIED",
				Message:   "Host mismatch",
			})
			return
		}
		req := &http.Request{Header: http.Header{}}
		err := cfg.Authenticate(req)
		if err != nil {
			l.replyJson(ctx, w, 403, apierr.APIErrorBody{
				ErrorCode: "PERMISSION_DENIED",
				Message:   err.Error(),
			})
			return
		}
		tokenType, accessToken, ok := strings.Cut(req.Header.Get("Authorization"), " ")
		if !ok {
			l.replyJson(ctx, w, 400, apierr.APIErrorBody{
				ErrorCode: "BAD_REQUEST",
				Message:   "Wrong Authorization header",
			})
		}
		l.replyJson(ctx, w, 200, msiToken{
			TokenType:   tokenType,
			AccessToken: accessToken,
			// for the sake of simplicity, we always expire tokens within 2 minutes
			ExpiresOn: json.Number(fmt.Sprint(time.Now().Add(2 * time.Minute).Unix())),
		})
	}))
}

func (l *loadedEnv) replyJson(ctx context.Context, w http.ResponseWriter, status int, body any) {
	msg := "<token response>"
	apiErrBody, ok := body.(apierr.APIErrorBody)
	if ok {
		msg = fmt.Sprintf("%s: %s", apiErrBody.ErrorCode, apiErrBody.Message)
	}
	logger.Debugf(ctx, "reply from metadata server: (%d) %s", status, msg)
	raw, err := json.Marshal(body)
	if err != nil {
		logger.Errorf(ctx, "json write: %s", err)
		w.WriteHeader(500)
		return
	}
	w.WriteHeader(status)
	w.Write(raw)
}
