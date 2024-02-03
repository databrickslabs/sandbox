package boilerplate

import (
	"archive/zip"
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/Azure/azure-sdk-for-go/sdk/storage/azblob/blob"
	"github.com/Azure/azure-sdk-for-go/sdk/storage/azblob/blockblob"
	"github.com/databricks/databricks-sdk-go/httpclient"
	"github.com/databrickslabs/sandbox/go-libs/env"
	"golang.org/x/oauth2/jws"
)

const ArtifactDirEnv = "DATABRICKS_LABS_ACTIONS_ARTIFACT_DIR"

// This file relies on undocumented APIs of GitHub Actions. See more details at:
//
// Sep 2022:
// - https://github.com/actions/upload-artifact/issues/180#issuecomment-1086306269
// - https://github.com/actions/upload-artifact/issues/180#issuecomment-1301521285
//
// Jan 2024:
// - https://github.dev/actions/toolkit/blob/main/packages/artifact/src/internal/upload/upload-artifact.ts

type artifactUploader struct {
	client       *httpclient.ApiClient
	runtimeToken string
}

func newUploader(ctx context.Context) *artifactUploader {
	runtimeToken := env.Get(ctx, "ACTIONS_RUNTIME_TOKEN")
	resultsServiceUrl := env.Get(ctx, "ACTIONS_RESULTS_URL")
	return &artifactUploader{
		runtimeToken: runtimeToken,
		client: httpclient.NewApiClient(httpclient.ClientConfig{
			Visitors: []httpclient.RequestVisitor{func(r *http.Request) error {
				r.Header.Add("Authorization", fmt.Sprintf("Bearer %s", runtimeToken))
				url, err := url.Parse(resultsServiceUrl)
				if err != nil {
					return err
				}
				r.URL.Host = url.Host
				r.URL.Scheme = url.Scheme
				return nil
			}},
		}),
	}
}

type uploadMetadata struct {
	ArtifactID int64
	Len        int
}

func (u *artifactUploader) Upload(ctx context.Context, name, folder string) (*uploadMetadata, error) {
	runID, jobRunID, err := u.backendIdsFromToken()
	if err != nil {
		return nil, fmt.Errorf("backend ids: %w", err)
	}
	createResp, err := u.createArtifact(ctx, createArtifactRequest{
		RunID:    runID,
		JobRunID: jobRunID,
		Name:     name,
		Version:  4,
	})
	if err != nil {
		return nil, fmt.Errorf("create: %w", err)
	}
	if !createResp.Ok {
		return nil, fmt.Errorf("cannot get pre-signed URL")
	}
	folderZip, err := u.folderZipStream(ctx, folder)
	if err != nil {
		return nil, fmt.Errorf("zip: %w", err)
	}
	sha256 := hex.EncodeToString(sha256.New().Sum(folderZip.Bytes()))
	err = u.uploadToAzureBlob(ctx, createResp.SignedUploadUrl, folderZip)
	if err != nil {
		return nil, fmt.Errorf("pre-signed: %w", err)
	}
	finalizeResp, err := u.finalizeArtifact(ctx, finalizeArtifactRequest{
		RunID:    runID,
		JobRunID: jobRunID,
		Hash:     fmt.Sprintf("sha256:%s", sha256),
		Size:     folderZip.Len(),
		Name:     name,
	})
	if err != nil {
		return nil, fmt.Errorf("finalize: %w", err)
	}
	if !finalizeResp.Ok {
		return nil, fmt.Errorf("cannot finalize")
	}
	return &uploadMetadata{
		ArtifactID: finalizeResp.ArtifactId,
		Len:        folderZip.Len(),
	}, nil
}

func (u *artifactUploader) uploadToAzureBlob(ctx context.Context, uploadURL string, zipStream *bytes.Buffer) error {
	bb, err := blockblob.NewClientWithNoCredential(uploadURL, nil)
	if err != nil {
		return fmt.Errorf("sas client: %w", err)
	}
	blobContentType := "zip"
	_, err = bb.UploadStream(ctx, zipStream, &blockblob.UploadStreamOptions{
		HTTPHeaders: &blob.HTTPHeaders{
			BlobContentType: &blobContentType,
		},
	})
	return fmt.Errorf("upload stream: %w", err)
}

func (u *artifactUploader) folderZipStream(ctx context.Context, folder string) (*bytes.Buffer, error) {
	var buf *bytes.Buffer
	zipWriter := zip.NewWriter(buf)
	defer zipWriter.Close()
	return buf, filepath.Walk(folder, func(filePath string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}
		rel, err := filepath.Rel(folder, filePath)
		if err != nil {
			return fmt.Errorf("rel: %w", err)
		}
		entry, err := zipWriter.Create(rel)
		if err != nil {
			return fmt.Errorf("zip entry: %w", err)
		}
		src, err := os.Open(filePath)
		if err != nil {
			return fmt.Errorf("open: %w", err)
		}
		defer src.Close()
		_, err = io.Copy(entry, src)
		return fmt.Errorf("copy: %w", err)
	})
}

// See https://github.com/actions/toolkit/blob/415c42d27ca2a24f3801dd9406344aaea00b7866/packages/artifact/src/internal/shared/util.ts#L22-L69
func (u *artifactUploader) backendIdsFromToken() (string, string, error) {
	claims, err := jws.Decode(u.runtimeToken)
	if err != nil {
		return "", "", fmt.Errorf("jws: %w", err)
	}
	// OAuth2 & JWT are soooo standard, that there are dozens of different implementations...
	scope, ok := claims.PrivateClaims["scp"].(string)
	if !ok {
		scope = claims.Scope
	}
	scopes := strings.Split(scope, " ")
	for _, scope := range scopes {
		parts := strings.Split(scope, ":")
		if parts[0] != "Actions.Results" {
			continue
		}
		if len(parts) != 3 {
			return "", "", fmt.Errorf("invalid scope: %s", scope)
		}
		runID, jobRunID := parts[1], parts[2]
		return runID, jobRunID, nil
	}
	return "", "", fmt.Errorf("invalid claims")
}

type createArtifactRequest struct {
	RunID    string `json:"workflowRunBackendId"`
	JobRunID string `json:"workflowJobRunBackendId"`
	Name     string `json:"name"`
	Version  int32  `json:"version"`

	ExpiresAt *time.Time `json:"expiresAt,omitempty"`
}

type createArtifactResponse struct {
	Ok              bool   `json:"ok"`
	SignedUploadUrl string `json:"signed_upload_url"`
}

func (u *artifactUploader) createArtifact(ctx context.Context, req createArtifactRequest) (*createArtifactResponse, error) {
	var res createArtifactResponse
	err := u.client.Do(ctx, "POST", "/github.actions.results.api.v1.ArtifactService/CreateArtifact",
		httpclient.WithRequestData(req),
		httpclient.WithResponseUnmarshal(&res))
	if err != nil {
		return nil, err
	}
	return &res, nil
}

type finalizeArtifactRequest struct {
	RunID    string `json:"workflowRunBackendId"`
	JobRunID string `json:"workflowJobRunBackendId"`
	Name     string `json:"name"`
	Size     int    `json:"size"`
	Hash     string `json:"hash,omitempty"`
}

type finalizeArtifactResponse struct {
	Ok         bool  `json:"ok"`
	ArtifactId int64 `json:"artifactId"`
}

func (u *artifactUploader) finalizeArtifact(ctx context.Context, req finalizeArtifactRequest) (*finalizeArtifactResponse, error) {
	var res finalizeArtifactResponse
	err := u.client.Do(ctx, "POST", "/github.actions.results.api.v1.ArtifactService/FinalizeArtifact",
		httpclient.WithRequestData(req),
		httpclient.WithResponseUnmarshal(&res))
	if err != nil {
		return nil, err
	}
	return &res, nil
}
