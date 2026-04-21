package testenv

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/databricks/databricks-sdk-go/apierr"
	"github.com/databricks/databricks-sdk-go/common/environment"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoadedEnv_Name(t *testing.T) {
	l := &loadedEnv{}
	assert.Equal(t, "azure-key-vault", l.Name())
}

func TestParseExpiryDate_Valid(t *testing.T) {
	exp := time.Now().Add(1 * time.Hour).Unix()
	claims := map[string]any{"exp": float64(exp)}
	payload, _ := json.Marshal(claims)
	token := fmt.Sprintf("header.%s.signature",
		base64.RawURLEncoding.EncodeToString(payload))

	l := &loadedEnv{}
	result, err := l.parseExpiryDate(context.Background(), token)
	require.NoError(t, err)
	assert.Equal(t, exp, result)
}

func TestParseExpiryDate_InvalidTokenFormat(t *testing.T) {
	l := &loadedEnv{}
	_, err := l.parseExpiryDate(context.Background(), "not-a-jwt")
	assert.ErrorContains(t, err, "invalid token format")
}

func TestParseExpiryDate_TwoParts(t *testing.T) {
	l := &loadedEnv{}
	_, err := l.parseExpiryDate(context.Background(), "header.payload")
	assert.ErrorContains(t, err, "invalid token format")
}

func TestParseExpiryDate_InvalidBase64(t *testing.T) {
	l := &loadedEnv{}
	_, err := l.parseExpiryDate(context.Background(), "header.!!!.signature")
	assert.ErrorContains(t, err, "payload")
}

func TestParseExpiryDate_InvalidJSON(t *testing.T) {
	payload := base64.RawURLEncoding.EncodeToString([]byte("not json"))
	l := &loadedEnv{}
	_, err := l.parseExpiryDate(context.Background(), fmt.Sprintf("header.%s.signature", payload))
	assert.ErrorContains(t, err, "json")
}

func TestParseExpiryDate_NoExpClaim(t *testing.T) {
	claims := map[string]any{"sub": "user123"}
	payload, _ := json.Marshal(claims)
	token := fmt.Sprintf("header.%s.signature",
		base64.RawURLEncoding.EncodeToString(payload))

	l := &loadedEnv{}
	_, err := l.parseExpiryDate(context.Background(), token)
	assert.ErrorContains(t, err, "not found")
}

func TestReplyJson_Success(t *testing.T) {
	l := &loadedEnv{}
	w := httptest.NewRecorder()
	body := map[string]string{"key": "value"}
	l.replyJson(context.Background(), w, 200, body)

	assert.Equal(t, 200, w.Code)
	var result map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &result)
	require.NoError(t, err)
	assert.Equal(t, "value", result["key"])
}

func TestReplyJson_APIError(t *testing.T) {
	l := &loadedEnv{}
	w := httptest.NewRecorder()
	l.replyJson(context.Background(), w, 400, apierr.APIError{
		ErrorCode: "BAD_REQUEST",
		Message:   "something went wrong",
	})

	assert.Equal(t, 400, w.Code)
}

func TestReplyJson_TokenResponse(t *testing.T) {
	l := &loadedEnv{}
	w := httptest.NewRecorder()
	l.replyJson(context.Background(), w, 200, msiToken{
		TokenType:   "Bearer",
		AccessToken: "token123",
		ExpiresOn:   json.Number("1234567890"),
	})

	assert.Equal(t, 200, w.Code)
	var result msiToken
	err := json.Unmarshal(w.Body.Bytes(), &result)
	require.NoError(t, err)
	assert.Equal(t, "Bearer", result.TokenType)
	assert.Equal(t, "token123", result.AccessToken)
}

func TestRedaction(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{
			"SECRET_KEY": "supersecret",
		},
	}
	r := l.Redaction()
	assert.NotNil(t, r)
}

func TestConfigure_SetsHostFromVars(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{
			"DATABRICKS_HOST": "https://test.cloud.databricks.com",
		},
	}
	cfg := &config.Config{}
	err := l.Configure(cfg)
	require.NoError(t, err)
	assert.Equal(t, "https://test.cloud.databricks.com", cfg.Host)
}

func TestConfigure_DoesNotOverwriteExisting(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{
			"DATABRICKS_HOST": "https://overwrite.databricks.com",
		},
	}
	cfg := &config.Config{
		Host: "https://existing.databricks.com",
	}
	err := l.Configure(cfg)
	require.NoError(t, err)
	assert.Equal(t, "https://existing.databricks.com", cfg.Host)
}

func TestConfigure_EmptyVars(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{},
	}
	cfg := &config.Config{}
	err := l.Configure(cfg)
	require.NoError(t, err)
}

func TestConfigure_SetsToken(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{
			"DATABRICKS_TOKEN": "dapi123",
		},
	}
	cfg := &config.Config{}
	err := l.Configure(cfg)
	require.NoError(t, err)
	assert.Equal(t, "dapi123", cfg.Token)
}

func TestCloud_WithAWSHost(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{
			"DATABRICKS_HOST":  "https://dbc-123.cloud.databricks.com",
			"DATABRICKS_TOKEN": "dapi123",
		},
	}
	cloud := l.Cloud()
	assert.Equal(t, environment.CloudAWS, cloud)
}

func TestCloud_WithAzureHost_NilVault(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{
			"DATABRICKS_HOST":  "https://adb-123.azuredatabricks.net",
			"DATABRICKS_TOKEN": "dapi123",
		},
	}
	// Config resolution fails because vault is nil for Azure
	cloud := l.Cloud()
	assert.Equal(t, environment.CloudAWS, cloud)
}

func TestConfigure_AzureWithNilVault(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{
			"DATABRICKS_HOST": "https://adb-123.azuredatabricks.net",
		},
	}
	cfg := &config.Config{}
	err := l.Configure(cfg)
	assert.ErrorContains(t, err, "azure credentials provider is not configured")
}

func TestCloud_NoVars(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{},
	}
	// When config resolution fails, defaults to AWS
	cloud := l.Cloud()
	assert.Equal(t, environment.CloudAWS, cloud)
}

func TestGetDatabricksConfig(t *testing.T) {
	l := &loadedEnv{
		vars: map[string]string{
			"DATABRICKS_HOST":  "https://test.cloud.databricks.com",
			"DATABRICKS_TOKEN": "dapi123",
		},
	}
	cfg, err := l.getDatabricksConfig()
	require.NoError(t, err)
	assert.Equal(t, "https://test.cloud.databricks.com", cfg.Host)
}

func TestMetadataServer_VersionMismatch(t *testing.T) {
	l := &loadedEnv{
		mpath: "test-path",
		vars: map[string]string{
			"DATABRICKS_HOST":  "https://test.cloud.databricks.com",
			"DATABRICKS_TOKEN": "dapi123",
		},
	}
	cfg, err := l.getDatabricksConfig()
	require.NoError(t, err)

	srv := l.metadataServer(cfg)
	defer srv.Close()

	// No metadata version header
	req, err := http.NewRequest("GET", srv.URL+"/test-path", nil)
	require.NoError(t, err)
	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, 400, resp.StatusCode)
}

func TestMetadataServer_WrongPath(t *testing.T) {
	l := &loadedEnv{
		mpath: "correct-path",
		vars: map[string]string{
			"DATABRICKS_HOST":  "https://test.cloud.databricks.com",
			"DATABRICKS_TOKEN": "dapi123",
		},
	}
	cfg, err := l.getDatabricksConfig()
	require.NoError(t, err)

	srv := l.metadataServer(cfg)
	defer srv.Close()

	req, err := http.NewRequest("GET", srv.URL+"/wrong-path", nil)
	require.NoError(t, err)
	req.Header.Set("X-Databricks-Metadata-Version", "1")
	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, 404, resp.StatusCode)
}

func TestMetadataServer_UnknownHost(t *testing.T) {
	l := &loadedEnv{
		mpath: "test-path",
		vars: map[string]string{
			"DATABRICKS_HOST":  "https://test.cloud.databricks.com",
			"DATABRICKS_TOKEN": "dapi123",
		},
	}
	cfg, err := l.getDatabricksConfig()
	require.NoError(t, err)

	srv := l.metadataServer(cfg)
	defer srv.Close()

	req, err := http.NewRequest("GET", srv.URL+"/test-path", nil)
	require.NoError(t, err)
	req.Header.Set("X-Databricks-Metadata-Version", "1")
	req.Header.Set("X-Databricks-Host", "https://unknown.databricks.com")
	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, 403, resp.StatusCode)
}

func TestMetadataServer_ValidRequest(t *testing.T) {
	l := &loadedEnv{
		mpath: "test-path",
		vars: map[string]string{
			"DATABRICKS_HOST":  "https://test.cloud.databricks.com",
			"DATABRICKS_TOKEN": "dapi123",
		},
	}
	cfg, err := l.getDatabricksConfig()
	require.NoError(t, err)

	srv := l.metadataServer(cfg)
	defer srv.Close()

	req, err := http.NewRequest("GET", srv.URL+"/test-path", nil)
	require.NoError(t, err)
	req.Header.Set("X-Databricks-Metadata-Version", "1")
	req.Header.Set("X-Databricks-Host", cfg.CanonicalHostName())
	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Equal(t, 200, resp.StatusCode)

	var token msiToken
	err = json.NewDecoder(resp.Body).Decode(&token)
	require.NoError(t, err)
	assert.Equal(t, "Bearer", token.TokenType)
	assert.Equal(t, "dapi123", token.AccessToken)
}

func TestStart(t *testing.T) {
	l := &loadedEnv{
		mpath: "test-path",
		vars: map[string]string{
			"DATABRICKS_HOST":  "https://test.cloud.databricks.com",
			"DATABRICKS_TOKEN": "dapi123",
			"SOME_VAR":         "some-value",
		},
	}
	ctx, cleanup, err := l.Start(context.Background())
	require.NoError(t, err)
	defer cleanup()

	assert.NotNil(t, ctx)
}
