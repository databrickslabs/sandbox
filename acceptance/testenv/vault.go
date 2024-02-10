package testenv

import (
	"context"
	"encoding/base64"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets"
	"github.com/databricks/databricks-sdk-go/config"
)

type creds interface {
	config.CredentialsProvider
	azcore.TokenCredential
}

type vaultEnv struct {
	vaultURI string
	creds    creds
}

func (v *vaultEnv) Load(ctx context.Context) (*loadedEnv, error) {
	vault, err := azsecrets.NewClient(v.vaultURI, v.creds, nil)
	if err != nil {
		return nil, fmt.Errorf("azsecrets.NewClient: %w", err)
	}
	pager := vault.NewListSecretsPager(nil)
	vars := map[string]string{}
	for pager.More() {
		page, err := pager.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("listing secrets from %s: %w", v.vaultURI, err)
		}
		for _, secret := range page.Value {
			name := secret.ID.Name()
			sv, err := vault.GetSecret(ctx, name, secret.ID.Version(), nil)
			if err != nil {
				return nil, fmt.Errorf("get secret %s: %w", name, err)
			}
			vars[strings.ReplaceAll(name, "-", "_")] = *sv.Value
		}
	}
	vars, err = v.filterEnv(vars)
	if err != nil {
		return nil, err
	}
	return &loadedEnv{
		v:     v,
		vars:  vars,
		mpath: v.randomString(32),
	}, nil
}

func (v *vaultEnv) randomString(length int) string {
	rnd := rand.New(rand.NewSource(time.Now().UnixNano()))
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	result := make([]byte, length)
	for i := range result {
		result[i] = charset[rnd.Intn(len(charset))]
	}
	return string(result)
}

func (v *vaultEnv) filterEnv(in map[string]string) (map[string]string, error) {
	out := map[string]string{}
	for k, v := range in {
		if k == "github_token" {
			// this is an internal token for github actions.
			// skipping it to avoid potential confusion.
			// perhaps it might be useful in some cases.
			continue
		}
		if k == "GOOGLE_CREDENTIALS" {
			googleCreds, err := base64.StdEncoding.DecodeString(v)
			if err != nil {
				return nil, fmt.Errorf("cannot decode google creds: %w", err)
			}
			v = strings.ReplaceAll(string(googleCreds), "\n", "")
		}
		out[k] = v
	}
	return out, nil
}
