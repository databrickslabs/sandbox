package testenv

import (
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databricks/databricks-sdk-go/config/credentials"
)

func NewWithAzureCLI(vaultURI string) *vaultEnv {
	return &vaultEnv{
		vaultURI: vaultURI,
		creds:    newAzureCliCreds(),
	}
}

type azureCliCreds struct {
	config.AzureCliCredentials
	*azidentity.AzureCLICredential
	credentials.CredentialsProvider
}

func newAzureCliCreds() *azureCliCreds {
	// this method doesn't return an error
	tc, _ := azidentity.NewAzureCLICredential(nil)
	return &azureCliCreds{
		AzureCLICredential: tc,
	}
}
