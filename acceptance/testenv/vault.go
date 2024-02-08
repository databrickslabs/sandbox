package testenv

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"math/rand"
	"net/url"
	"strings"
	"time"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets"

	"github.com/sethvargo/go-githubactions"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/clientcredentials"
)

func New(a *githubactions.Action, vaultURI string) *vaultEnv {
	return &vaultEnv{
		a:        a, // TODO: inject via Load(), when integrating with CLI
		vaultURI: vaultURI,
	}
}

type vaultEnv struct {
	a *githubactions.Action

	vaultURI string
}

func (v *vaultEnv) Load(ctx context.Context) (*loadedEnv, error) {
	cred, err := v.getMsalCredential()
	if err != nil {
		return nil, fmt.Errorf("credential: %w", err)
	}
	vault, err := azsecrets.NewClient(v.vaultURI, cred, nil)
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

func (v *vaultEnv) getMsalCredential() (azcore.TokenCredential, error) {
	return v, nil // TODO: do it better
	// azCli, err := azidentity.NewAzureCLICredential(nil)
	// if err != nil {
	// 	return nil, err
	// }
	// return azidentity.NewChainedTokenCredential([]azcore.TokenCredential{azCli, v}, nil)
}

func (v *vaultEnv) oidcTokenSource(ctx context.Context, resource string) (oauth2.TokenSource, error) {
	clientAssertion, err := v.a.GetIDToken(ctx, "api://AzureADTokenExchange")
	if err != nil {
		return nil, fmt.Errorf("id token: %w", err)
	}
	clientID := v.a.Getenv("ARM_CLIENT_ID")
	tenantID := v.a.Getenv("ARM_TENANT_ID")
	return (&clientcredentials.Config{
		ClientID: clientID,
		TokenURL: fmt.Sprintf("https://login.microsoftonline.com/%s/oauth2/token", tenantID),
		EndpointParams: url.Values{
			"client_assertion_type": []string{"urn:ietf:params:oauth:client-assertion-type:jwt-bearer"},
			"client_assertion":      []string{clientAssertion},
			"resource":              []string{resource},
		},
	}).TokenSource(ctx), nil
}

// GetToken implements azcore.TokenCredential to talk to Azure Key Vault
func (v *vaultEnv) GetToken(ctx context.Context, options policy.TokenRequestOptions) (azcore.AccessToken, error) {
	ts, err := v.oidcTokenSource(ctx, options.Scopes[0])
	if err != nil {
		return azcore.AccessToken{}, err
	}
	token, err := ts.Token()
	if err != nil {
		return azcore.AccessToken{}, err
	}
	return azcore.AccessToken{
		Token:     token.AccessToken,
		ExpiresOn: token.Expiry,
	}, nil
}

type oidcCredential struct {
	a        *githubactions.Action
	resource string
}

type msiToken struct {
	TokenType    string      `json:"token_type"`
	AccessToken  string      `json:"access_token,omitempty"`
	RefreshToken string      `json:"refresh_token,omitempty"`
	ExpiresOn    json.Number `json:"expires_on"`
}
