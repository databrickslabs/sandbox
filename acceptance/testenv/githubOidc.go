package testenv

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/sethvargo/go-githubactions"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/clientcredentials"
)

func NewWithGitHubOIDC(a *githubactions.Action, vaultURI string) *vaultEnv {
	return &vaultEnv{
		vaultURI: vaultURI,
		creds:    &ghOidcCreds{a},
	}
}

type ghOidcCreds struct {
	a *githubactions.Action
}

func (c *ghOidcCreds) oidcTokenSource(ctx context.Context, resource string) (oauth2.TokenSource, error) {
	// TODO: at the moment, ID token expires in 1 hour, so we need to rewrite the logic to refresh it
	clientAssertion, err := c.a.GetIDToken(ctx, "api://AzureADTokenExchange")
	if err != nil {
		return nil, fmt.Errorf("id token: %w", err)
	}
	clientID := c.a.Getenv("ARM_CLIENT_ID")
	tenantID := c.a.Getenv("ARM_TENANT_ID")
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

func (c *ghOidcCreds) Name() string {
	return "github-oidc"
}

// Configure implements credentials provider for Databricks SDK
func (c *ghOidcCreds) Configure(ctx context.Context, cfg *config.Config) (func(*http.Request) error, error) {
	ts, err := c.oidcTokenSource(ctx, cfg.Environment().AzureApplicationID)
	if err != nil {
		return nil, fmt.Errorf("oidc: %w", err)
	}
	return func(r *http.Request) error {
		token, err := ts.Token()
		if err != nil {
			return fmt.Errorf("token: %w", err)
		}
		token.SetAuthHeader(r)
		return nil
	}, nil
}

// GetToken implements azcore.TokenCredential to talk to Azure Key Vault
func (c *ghOidcCreds) GetToken(ctx context.Context, options policy.TokenRequestOptions) (azcore.AccessToken, error) {
	scope := strings.TrimSuffix(options.Scopes[0], "/.default")
	ts, err := c.oidcTokenSource(ctx, scope)
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

type msiToken struct {
	TokenType    string      `json:"token_type"`
	AccessToken  string      `json:"access_token,omitempty"`
	RefreshToken string      `json:"refresh_token,omitempty"`
	ExpiresOn    json.Number `json:"expires_on"`
}
