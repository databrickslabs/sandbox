package github

import (
	"context"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"strings"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/jws"
)

type GitHubTokenSource struct {
	// The primary rate limit for unauthenticated requests is 60 requests per hour.
	Anonymous bool
	
	// Users have personal rate limit of 5,000 requests per hour.
	//
	// You can use the built-in GITHUB_TOKEN to authenticate requests in 
	// GitHub Actions workflows: the rate limit for GITHUB_TOKEN is 1,000 requests 
	// per hour per repository. For requests to resources that belong to a GitHub 
	// Enterprise Cloud account, the limit is 15,000 requests per hour per repository.
	Pat string
	
	// Requests made on your behalf by a GitHub App that is owned by
	// a GitHub Enterprise Cloud organization have a higher rate limit
	// of 15,000 requests per hour.
	//
	// For installations that are not on a GitHub Enterprise Cloud organization, 
	// the rate limit for the installation will scale with the number of users 
	// and repositories. Installations that have more than 20 repositories receive 
	// another 50 requests per hour for each repository. Installations that are on 
	// an organization that have more than 20 users receive another 50 requests per 
	// hour for each user. The rate limit cannot increase beyond 12,500 requests 
	// per hour.
	ApplicationID    int64
	InstallationID   int
	PrivateKeyPath   string
	PrivateKeyBase64 string

	cached oauth2.TokenSource
}

func (g *GitHubTokenSource) Token() (*oauth2.Token, error) {
	if g.Pat != "" {
		return &oauth2.Token{
			AccessToken: g.Pat,
		}, nil
	}
	if g.Anonymous {
		return &oauth2.Token{}, nil
	}
	if g.cached != nil {
		return g.cached.Token()
	}
	for _, ts := range []oauth2.TokenSource{
		&ghEnvTokenSource{"GITHUB_TOKEN"},
		&ghInstallationTokenSource{g},
		&ghCliTokenSource{},
		&anonymousTokenSource{},
	} {
		token, err := ts.Token()
		if errors.Is(err, fs.ErrNotExist) {
			continue
		} else if err != nil {
			return nil, err
		}
		g.cached = oauth2.ReuseTokenSource(token, ts)
		return token, nil
	}
	return nil, fmt.Errorf("no github token available")
}

type anonymousTokenSource struct{}

func (e *anonymousTokenSource) Token() (*oauth2.Token, error) {
	return &oauth2.Token{}, nil
}

type ghEnvTokenSource struct {
	Name string
}

func (e *ghEnvTokenSource) Token() (*oauth2.Token, error) {
	if e.Name == "" {
		return nil, fs.ErrNotExist
	}
	value, ok := os.LookupEnv(e.Name)
	if !ok {
		return nil, fs.ErrNotExist
	}
	return &oauth2.Token{
		TokenType:   "Bearer",
		AccessToken: value,
	}, nil
}

type ghCliTokenSource struct {
	Path string
}

func (cli *ghCliTokenSource) Token() (*oauth2.Token, error) {
	if cli.Path == "" {
		cli.Path = "gh"
	}
	result, err := exec.Command(cli.Path, "auth", "token").Output()
	if err != nil {
		// we just skip this token source on error
		return nil, fs.ErrNotExist
	}
	return &oauth2.Token{
		TokenType:   "Bearer",
		AccessToken: strings.TrimSpace(string(result)),
	}, nil
}

func (g *GitHubTokenSource) getPrivateKeyBytes() ([]byte, error) {
	if g.PrivateKeyBase64 != "" {
		return base64.RawStdEncoding.DecodeString(g.PrivateKeyBase64)
	}
	path := g.PrivateKeyPath
	if home, err := os.UserHomeDir(); err == nil {
		path = strings.ReplaceAll(path, "~", home)
	}
	return os.ReadFile(path)
}

// See listed claims at:
// https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app
type ghAppTokenSource struct {
	*GitHubTokenSource
}

func (g *ghAppTokenSource) Token() (*oauth2.Token, error) {
	privateKeyBytes, err := g.getPrivateKeyBytes()
	if err != nil {
		return nil, err
	}
	block, _ := pem.Decode(privateKeyBytes)
	if block != nil {
		privateKeyBytes = block.Bytes
	}
	parsedKey, err := x509.ParsePKCS1PrivateKey(privateKeyBytes)
	if err != nil {
		return nil, err
	}
	iat := time.Now().Add(-30 * time.Second)
	exp := iat.Add(5 * time.Minute)
	payload, err := jws.Encode(&jws.Header{Algorithm: "RS256", Typ: "JWT"}, &jws.ClaimSet{
		Iat: iat.Unix(),
		Exp: exp.Unix(),
		Iss: fmt.Sprint(g.ApplicationID),
	}, parsedKey)
	if err != nil {
		return nil, err
	}
	return &oauth2.Token{
		TokenType:   "Bearer",
		AccessToken: payload,
		Expiry:      exp,
	}, nil
}

// See "Generating an installation access token" section:
// https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
type ghInstallationTokenSource struct {
	*GitHubTokenSource
}

func (i *ghInstallationTokenSource) Token() (*oauth2.Token, error) {
	ctx := context.Background()
	client := oauth2.NewClient(ctx, &ghAppTokenSource{i.GitHubTokenSource})
	tokenURL := fmt.Sprintf("https://api.github.com/app/installations/%d/access_tokens", i.InstallationID)
	resp, err := client.Post(tokenURL, "application/vnd.github+json", nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	var installationToken struct {
		Token               string            `json:"token"`
		ExpiresAt           time.Time         `json:"expires_at"`
		Permissions         map[string]string `json:"permissions"`
		RepositorySelection any               `json:"repository_selection"`
	}
	err = json.NewDecoder(resp.Body).Decode(&installationToken)
	if err != nil {
		return nil, err
	}
	return &oauth2.Token{
		TokenType:   "Bearer",
		AccessToken: installationToken.Token,
		Expiry:      installationToken.ExpiresAt,
	}, nil
}
