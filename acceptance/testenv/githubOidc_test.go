package testenv

import (
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestGhOidcCreds_Name(t *testing.T) {
	c := &ghOidcCreds{}
	assert.Equal(t, "github-oidc", c.Name())
}

func TestCredentialsProviderFunc_SetHeaders(t *testing.T) {
	cpf := &credentialsProviderFunc{
		setHeadersFunc: func(r *http.Request) error {
			r.Header.Set("Authorization", "Bearer test-token")
			return nil
		},
	}
	req, err := http.NewRequest("GET", "http://example.com", nil)
	require.NoError(t, err)
	err = cpf.SetHeaders(req)
	require.NoError(t, err)
	assert.Equal(t, "Bearer test-token", req.Header.Get("Authorization"))
}

func TestCredentialsProviderFunc_SetHeaders_Error(t *testing.T) {
	cpf := &credentialsProviderFunc{
		setHeadersFunc: func(r *http.Request) error {
			return assert.AnError
		},
	}
	req, err := http.NewRequest("GET", "http://example.com", nil)
	require.NoError(t, err)
	err = cpf.SetHeaders(req)
	assert.Error(t, err)
}
