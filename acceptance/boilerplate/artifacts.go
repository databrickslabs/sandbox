package boilerplate

import (
	"context"
	"fmt"
	"net/http"
	"os"

	"github.com/databricks/databricks-sdk-go/httpclient"
)

// See https://github.com/actions/upload-artifact/issues/180#issuecomment-1301521285

type artifactUploader struct {
	client *httpclient.ApiClient
}

func newUploader() *artifactUploader {
	return &artifactUploader{
		client: httpclient.NewApiClient(httpclient.ClientConfig{
			Visitors: []httpclient.RequestVisitor{func(r *http.Request) error {
				r.Header.Add("Accept", "application/json;api-version=6.0-preview")
				r.Header.Add("Authorization", fmt.Sprintf("Bearer %s", os.Getenv("ACTIONS_RUNTIME_TOKEN")))
				return nil
			}},
		}),
	}
}

func (u *artifactUploader) uploadArtifact(ctx context.Context, artifactName string, buf []byte) error {
	baseUrl := fmt.Sprintf("%s_apis/pipelines/workflows/%s/artifacts?api-version=6.0-preview",
		os.Getenv("ACTIONS_RUNTIME_URL"),
		os.Getenv("GITHUB_RUN_ID"))
	var fc struct {
		FileContainerResourceUrl string `json:"fileContainerResourceUrl"`
	}
	err := u.client.Do(ctx, "POST", baseUrl, httpclient.WithResponseUnmarshal(&fc))
	if err != nil {
		return err
	}
	resourceUrl := fmt.Sprintf("%s?itemPath=%s/data.txt", fc.FileContainerResourceUrl, artifactName)
	err = u.client.Do(ctx, "PUT", resourceUrl,
		httpclient.WithRequestData(buf),
		httpclient.WithRequestHeaders(map[string]string{
			"Content-Type":  "application/octet-stream",
			"Content-Range": fmt.Sprintf("bytes 0-%d/%d", len(buf)-1, len(buf)),
		}))
	if err != nil {
		return err
	}
	finalizeUrl := fmt.Sprintf("%s&artifactName=%s", baseUrl, artifactName)
	return u.client.Do(ctx, "PATCH", finalizeUrl, httpclient.WithRequestData(map[string]any{
		"size": len(buf),
	}))
}
