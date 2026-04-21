package ecosystem

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLocalHookServer_URL(t *testing.T) {
	ctx := context.Background()
	srv := newLocalHookServer(ctx)
	defer srv.Close()
	assert.NotEmpty(t, srv.URL())
	assert.Contains(t, srv.URL(), "http://")
}

func TestLocalHookServer_PostAndReceive(t *testing.T) {
	ctx := context.Background()
	srv := newLocalHookServer(ctx)
	defer srv.Close()

	payload := map[string]string{"key": "value"}
	raw, err := json.Marshal(payload)
	require.NoError(t, err)

	go func() {
		resp, err := http.Post(srv.URL(), "application/json", bytes.NewReader(raw))
		if err == nil {
			resp.Body.Close()
		}
	}()

	var result map[string]string
	err = srv.Unmarshal(&result)
	require.NoError(t, err)
	assert.Equal(t, "value", result["key"])
}

func TestLocalHookServer_Unmarshal_ContextCancel(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	srv := newLocalHookServer(ctx)
	defer srv.Close()

	var result map[string]string
	err := srv.Unmarshal(&result)
	assert.Error(t, err)
}

func TestLocalHookServer_Close(t *testing.T) {
	ctx := context.Background()
	srv := newLocalHookServer(ctx)
	url := srv.URL()
	srv.Close()
	_, err := http.Post(url, "application/json", bytes.NewReader([]byte("{}")))
	assert.Error(t, err)
}
