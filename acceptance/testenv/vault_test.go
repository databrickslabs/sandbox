package testenv

import (
	"encoding/base64"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestRandomString_Length(t *testing.T) {
	v := &vaultEnv{}
	for _, length := range []int{0, 1, 10, 32, 64} {
		s := v.randomString(length)
		assert.Len(t, s, length)
	}
}

func TestRandomString_Charset(t *testing.T) {
	v := &vaultEnv{}
	s := v.randomString(1000)
	for _, c := range s {
		assert.True(t,
			(c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9'),
			"unexpected character: %c", c)
	}
}

func TestRandomString_Unique(t *testing.T) {
	v := &vaultEnv{}
	s1 := v.randomString(32)
	s2 := v.randomString(32)
	assert.NotEqual(t, s1, s2)
}

func TestFilterEnv_SkipsGitHubToken(t *testing.T) {
	v := &vaultEnv{}
	in := map[string]string{
		"github_token":    "secret",
		"DATABRICKS_HOST": "https://example.com",
	}
	out, err := v.filterEnv(in)
	require.NoError(t, err)
	assert.NotContains(t, out, "github_token")
	assert.Equal(t, "https://example.com", out["DATABRICKS_HOST"])
}

func TestFilterEnv_DecodesGoogleCredentials(t *testing.T) {
	v := &vaultEnv{}
	creds := `{"type":"service_account","project_id":"test"}`
	encoded := base64.StdEncoding.EncodeToString([]byte(creds))
	in := map[string]string{
		"GOOGLE_CREDENTIALS": encoded,
	}
	out, err := v.filterEnv(in)
	require.NoError(t, err)
	assert.Equal(t, `{"type":"service_account","project_id":"test"}`, out["GOOGLE_CREDENTIALS"])
}

func TestFilterEnv_GoogleCredentials_StripNewlines(t *testing.T) {
	v := &vaultEnv{}
	creds := "line1\nline2\nline3"
	encoded := base64.StdEncoding.EncodeToString([]byte(creds))
	in := map[string]string{
		"GOOGLE_CREDENTIALS": encoded,
	}
	out, err := v.filterEnv(in)
	require.NoError(t, err)
	assert.NotContains(t, out["GOOGLE_CREDENTIALS"], "\n")
	assert.Equal(t, "line1line2line3", out["GOOGLE_CREDENTIALS"])
}

func TestFilterEnv_InvalidGoogleCredentials(t *testing.T) {
	v := &vaultEnv{}
	in := map[string]string{
		"GOOGLE_CREDENTIALS": "not-valid-base64!!!",
	}
	_, err := v.filterEnv(in)
	assert.ErrorContains(t, err, "cannot decode google creds")
}

func TestFilterEnv_Empty(t *testing.T) {
	v := &vaultEnv{}
	out, err := v.filterEnv(map[string]string{})
	require.NoError(t, err)
	assert.Empty(t, out)
}

func TestFilterEnv_PassthroughOtherVars(t *testing.T) {
	v := &vaultEnv{}
	in := map[string]string{
		"VAR1": "value1",
		"VAR2": "value2",
	}
	out, err := v.filterEnv(in)
	require.NoError(t, err)
	assert.Equal(t, "value1", out["VAR1"])
	assert.Equal(t, "value2", out["VAR2"])
}
