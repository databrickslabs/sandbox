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
	if cfg.IsAzure() {
		cfg.Credentials = l.v.creds
	}
	for _, a := range config.ConfigAttributes {
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

func (l *loadedEnv) Cloud() config.Cloud {
	cfg, err := l.getDatabricksConfig()
	if err != nil {
		return config.CloudAWS
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
	accountConfig := &config.Config{}
	if seed.IsAzure() {
		logger.Debugf(context.Background(), "Configuring on Azure: (%s)", accountHost)
		accountConfig = &config.Config{
			Loaders:     []config.Loader{config.ConfigFile},
			Host:        accountHost,
			AccountID:   seed.AccountID,
			Credentials: l.v.creds,
		}
	}
	if seed.IsAws() {
		logger.Debugf(context.Background(), "Configuring on AWS: (%s)", seed.ClientID)
		accountConfig = &config.Config{
			Loaders:      []config.Loader{},
			Host:         accountHost,
			AccountID:    seed.AccountID,
			ClientID:     seed.ClientID,
			ClientSecret: seed.ClientSecret,
			Credentials:  seed.Credentials,
			AuthType:     "oauth-m2m",
		}
	}
	configurations := map[string]*config.Config{
		seed.CanonicalHostName(): seed,
		accountHost:              accountConfig,
	}
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer r.Body.Close()
		ctx := r.Context()
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
		hostInHeader := r.Header.Get("X-Databricks-Host")
		configs, ok := configurations[hostInHeader]
		if !ok {
			l.replyJson(ctx, w, 403, apierr.APIErrorBody{
				ErrorCode: "PERMISSION_DENIED",
				Message:   fmt.Sprintf("Not allowed: %s", hostInHeader),
			})
			return
		}
		req := &http.Request{Header: http.Header{}}
		err := configs.Authenticate(req)
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
			// TODO: get the real expiry of the token (if we can)
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
