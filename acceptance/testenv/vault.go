package testenv

import (
	"context"
	"encoding/base64"
	"fmt"
	"strings"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/Azure/azure-sdk-for-go/sdk/keyvault/azsecrets"
	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/sethvargo/go-githubactions"
)

type oidcCredential struct {
	a *githubactions.Action
}

func (o *oidcCredential) GetToken(ctx context.Context, options policy.TokenRequestOptions) (azcore.AccessToken, error) {
	clientAssertion, err := o.a.GetIDToken(ctx, "api://AzureADTokenExchange")
	if err != nil {
		return azcore.AccessToken{}, err
	}
	/* python reference implementation
	# get the ID Token with aud=api://AzureADTokenExchange sub=repo:org/repo:environment:name
	response_json = response.json()
	if 'value' not in response_json:
		return None

	logger.info("Configured AAD token for GitHub Actions OIDC (%s)", cfg.azure_client_id)
	params = {
		'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
		'resource': cfg.effective_azure_login_app_id,
		'client_assertion': response_json['value'],
	}
	aad_endpoint = cfg.arm_environment.active_directory_endpoint
	if not cfg.azure_tenant_id:
		# detect Azure AD Tenant ID if it's not specified directly
		token_endpoint = cfg.oidc_endpoints.token_endpoint
		cfg.azure_tenant_id = token_endpoint.replace(aad_endpoint, '').split('/')[0]
	inner = ClientCredentials(client_id=cfg.azure_client_id,
								client_secret="", # we have no (rotatable) secrets in OIDC flow
								token_url=f"{aad_endpoint}{cfg.azure_tenant_id}/oauth2/token",
								endpoint_params=params,
								use_params=True)

	def refreshed_headers() -> Dict[str, str]:
		token = inner.token()
		return {'Authorization': f'{token.token_type} {token.access_token}'}

	return refreshed_headers
	*/
	return azcore.AccessToken{
		Token: tok,
	}, nil
}

// also - there's OIDC integration:
// a.GetIDToken(ctx, "api://AzureADTokenExchange")

func envVars(ctx context.Context, vaultURI string) (map[string]string, error) {
	credential, err := azidentity.NewDefaultAzureCredential(nil)
	if err != nil {
		return nil, fmt.Errorf("azure default auth: %w", err)
	}
	logger.Infof(ctx, "Listing secrets from %s", vaultURI)
	vault, err := azsecrets.NewClient(vaultURI, credential, nil)
	if err != nil {
		return nil, fmt.Errorf("azsecrets.NewClient: %w", err)
	}
	pager := vault.NewListSecretsPager(nil)
	vars := map[string]string{}
	// implicit CLOUD_ENV var
	vars["CLOUD_ENV"] = env.must().Cloud()
	for pager.More() {
		page, err := pager.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("listing secrets from %s: %w", vaultURI, err)
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
	return filterEnv(vars)
}

func NewConfigFor(ctx context.Context) (*config.Config, error) {
	vars, err := envVars(ctx)
	if err != nil {
		return nil, fmt.Errorf("env vars: %w", err)
	}
	logger.Infof(ctx, "Creating *databricks.Config for %s env", env)
	cfg := &config.Config{}
	// TODO: add output redaction for secrets based on sensitive values
	for _, a := range config.ConfigAttributes {
		for _, ev := range a.EnvVars {
			v, ok := vars[ev]
			if !ok {
				continue
			}
			err = a.SetS(cfg, v)
			if err != nil {
				return nil, fmt.Errorf("set %s: %w", a.Name, err)
			}
		}
	}
	return cfg, cfg.EnsureResolved()
}

func filterEnv(in map[string]string) (map[string]string, error) {
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
