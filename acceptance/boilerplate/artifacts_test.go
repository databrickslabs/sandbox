package boilerplate

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func makeJWT(claims map[string]any) string {
	header := base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"HS256"}`))
	payload, _ := json.Marshal(claims)
	payloadB64 := base64.RawURLEncoding.EncodeToString(payload)
	return fmt.Sprintf("%s.%s.signature", header, payloadB64)
}

func TestBackendIdsFromToken_Valid(t *testing.T) {
	token := makeJWT(map[string]any{
		"scp": "Actions.Results:run123:job456 other:scope",
	})
	u := &artifactUploader{runtimeToken: token}
	runID, jobRunID, err := u.backendIdsFromToken()
	require.NoError(t, err)
	assert.Equal(t, "run123", runID)
	assert.Equal(t, "job456", jobRunID)
}

func TestBackendIdsFromToken_InvalidJWT(t *testing.T) {
	u := &artifactUploader{runtimeToken: "not-a-jwt"}
	_, _, err := u.backendIdsFromToken()
	assert.ErrorContains(t, err, "invalid jwt")
}

func TestBackendIdsFromToken_InvalidBase64(t *testing.T) {
	u := &artifactUploader{runtimeToken: "header.!!!invalid!!!.signature"}
	_, _, err := u.backendIdsFromToken()
	assert.ErrorContains(t, err, "base64")
}

func TestBackendIdsFromToken_InvalidJSON(t *testing.T) {
	payload := base64.RawURLEncoding.EncodeToString([]byte("not json"))
	u := &artifactUploader{runtimeToken: fmt.Sprintf("header.%s.sig", payload)}
	_, _, err := u.backendIdsFromToken()
	assert.ErrorContains(t, err, "json")
}

func TestBackendIdsFromToken_NoScope(t *testing.T) {
	token := makeJWT(map[string]any{
		"sub": "something",
	})
	u := &artifactUploader{runtimeToken: token}
	_, _, err := u.backendIdsFromToken()
	assert.ErrorContains(t, err, "no scope")
}

func TestBackendIdsFromToken_NoActionsResultsScope(t *testing.T) {
	token := makeJWT(map[string]any{
		"scp": "Other.Scope:val1:val2",
	})
	u := &artifactUploader{runtimeToken: token}
	_, _, err := u.backendIdsFromToken()
	assert.ErrorContains(t, err, "invalid claims")
}

func TestBackendIdsFromToken_InvalidScopeParts(t *testing.T) {
	token := makeJWT(map[string]any{
		"scp": "Actions.Results:only-one-part",
	})
	u := &artifactUploader{runtimeToken: token}
	_, _, err := u.backendIdsFromToken()
	assert.ErrorContains(t, err, "invalid scope")
}

func TestFolderZipStream_EmptyDir(t *testing.T) {
	dir := t.TempDir()
	u := &artifactUploader{}
	buf, err := u.folderZipStream(t.Context(), dir)
	require.NoError(t, err)
	assert.NotNil(t, buf)
	// zip with no entries still has some bytes for the end-of-central-directory
	assert.Greater(t, buf.Len(), 0)
}

func TestFolderZipStream_WithFiles(t *testing.T) {
	dir := t.TempDir()
	err := os.WriteFile(filepath.Join(dir, "file1.txt"), []byte("hello"), 0644)
	require.NoError(t, err)
	err = os.MkdirAll(filepath.Join(dir, "sub"), 0755)
	require.NoError(t, err)
	err = os.WriteFile(filepath.Join(dir, "sub", "file2.txt"), []byte("world"), 0644)
	require.NoError(t, err)

	u := &artifactUploader{}
	buf, err := u.folderZipStream(t.Context(), dir)
	require.NoError(t, err)
	assert.Greater(t, buf.Len(), 0)
}

func TestFolderZipStream_NonexistentDir(t *testing.T) {
	u := &artifactUploader{}
	_, err := u.folderZipStream(t.Context(), "/nonexistent/path")
	assert.Error(t, err)
}
