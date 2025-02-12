package testenv

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"time"

	"github.com/databricks/databricks-sdk-go/apierr"
	"github.com/databricks/databricks-sdk-go/common/environment"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/acceptance/redaction"
	"github.com/databrickslabs/sandbox/go-libs/env"
)

type loadedEnv struct {
	v     *vaultEnv
	mpath string
	vars  map[string]string
}

func (l *loadedEnv) Name() string {
	return "azure-key-vault"
}

// Configure implemets config.Loader interface
func (l *loadedEnv) Configure(cfg *config.Config) error {
	for _, a := range config.ConfigAttributes {
		if !a.IsZero(cfg) {
			continue
		}
		for _, ev := range a.EnvVars {
			v, ok := l.vars[ev]
			if !ok {
				continue
			}
			// TODO: redact only sensitive values out
			err := a.SetS(cfg, v)
			if err != nil {
				return fmt.Errorf("set %s: %w", a.Name, err)
			}
		}
	}
	if cfg.IsAzure() {
		cfg.Credentials = l.v.creds
	}
	return nil
}

func (l *loadedEnv) getDatabricksConfig() (*config.Config, error) {
	cfg := &config.Config{
		Loaders: []config.Loader{l},
	}
	return cfg, cfg.EnsureResolved()
}

func (l *loadedEnv) Redaction() redaction.Redaction {
	return redaction.New(l.vars)
}

func (l *loadedEnv) Cloud() environment.Cloud {
	cfg, err := l.getDatabricksConfig()
	if err != nil {
		return environment.CloudAWS
	}
	return cfg.Environment().Cloud
}

func (l *loadedEnv) Start(ctx context.Context) (context.Context, func(), error) {
	cfg, err := l.getDatabricksConfig()
	if err != nil {
		return nil, nil, fmt.Errorf("config: %w", err)
	}
	srv := l.metadataServer(cfg)
	ctx = env.Set(ctx, "CLOUD_ENV", strings.ToLower(string(cfg.Environment().Cloud)))
	ctx = env.Set(ctx, "DATABRICKS_METADATA_SERVICE_URL", fmt.Sprintf("%s/%s", srv.URL, l.mpath))
	ctx = env.Set(ctx, "DATABRICKS_AUTH_TYPE", "metadata-service")
	isAuth := map[string]bool{}
	for _, attr := range config.ConfigAttributes {
		for _, envVar := range attr.EnvVars {
			if attr.Auth == "" {
				continue
			}
			isAuth[envVar] = true
		}
	}
	for k, v := range l.vars {
		if isAuth[k] {
			// not to conflict with metadata service,
			// erase any auth env vars
			v = ""
		}
		ctx = env.Set(ctx, k, v)
	}
	return ctx, srv.Close, nil
}

func (l *loadedEnv) metadataServer(seed *config.Config) *httptest.Server {
	accountHost := seed.Environment().DeploymentURL("accounts")
	configurations := map[string]*config.Config{
		seed.CanonicalHostName(): seed,
		accountHost: {
			Loaders:   []config.Loader{l},
			Host:      accountHost,
			AccountID: seed.AccountID,
		},
	}
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer r.Body.Close()
		ctx := r.Context()
		if r.Header.Get("X-Databricks-Metadata-Version") != "1" {
			l.replyJson(ctx, w, 400, apierr.APIError{
				ErrorCode: "BAD_REQUEST",
				Message:   "Version mismatch",
			})
			return
		}
		if strings.TrimPrefix(r.URL.Path, "/") != l.mpath {
			l.replyJson(ctx, w, 404, apierr.APIError{
				ErrorCode: "NOT_FOUND",
				Message:   "nope",
			})
			return
		}
		hostInHeader := r.Header.Get("X-Databricks-Host")
		configs, ok := configurations[hostInHeader]
		if !ok {
			l.replyJson(ctx, w, 403, apierr.APIError{
				ErrorCode: "PERMISSION_DENIED",
				Message:   fmt.Sprintf("Not allowed: %s", hostInHeader),
			})
			return
		}
		req := &http.Request{Header: http.Header{}}
		err := configs.Authenticate(req)
		if err != nil {
			l.replyJson(ctx, w, 403, apierr.APIError{
				ErrorCode: "PERMISSION_DENIED",
				Message:   err.Error(),
			})
			return
		}
		tokenType, accessToken, ok := strings.Cut(req.Header.Get("Authorization"), " ")
		if !ok {
			l.replyJson(ctx, w, 400, apierr.APIError{
				ErrorCode: "BAD_REQUEST",
				Message:   "Wrong Authorization header",
			})
		}
		// try parse expiry date from JWT token
		exp, err := l.parseExpiryDate(ctx, accessToken)
		if err != nil {
			logger.Errorf(ctx, "parse expiry date: %s", err)
			exp = time.Now().Add(2 * time.Minute).Unix()
		}
		l.replyJson(ctx, w, 200, msiToken{
			TokenType:   tokenType,
			AccessToken: accessToken,
			ExpiresOn:   json.Number(fmt.Sprint(exp)),
		})
	}))
}

func (l *loadedEnv) parseExpiryDate(ctx context.Context, tokenString string) (int64, error) {
	parts := strings.Split(tokenString, ".")
	if len(parts) != 3 {
		return 0, fmt.Errorf("invalid token format")
	}
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return 0, fmt.Errorf("payload: %v", err)
	}
	var claims map[string]interface{}
	err = json.Unmarshal(payload, &claims)
	if err != nil {
		return 0, fmt.Errorf("json: %v", err)
	}
	exp, ok := claims["exp"].(float64)
	if ok {
		logger.Debugf(ctx, "exp is float64: %d", exp)
		return int64(exp), nil
	}
	expInt, ok := claims["exp"].(int64)
	if ok {
		logger.Debugf(ctx, "exp is int64: %d", expInt)
		return expInt, nil
	}
	return 0, fmt.Errorf("not found")
}

func (l *loadedEnv) replyJson(ctx context.Context, w http.ResponseWriter, status int, body any) {
	msg := "<token response>"
	apiErrBody, ok := body.(apierr.APIError)
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
