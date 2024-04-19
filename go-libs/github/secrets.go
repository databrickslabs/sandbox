package github

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"time"

	"golang.org/x/crypto/nacl/box"
)

type RepositorySecrets struct {
	TotalCount int                `json:"total_count"`
	Secrets    []RepositorySecret `json:"secrets"`
}

type RepositorySecret struct {
	Name      string    `json:"name"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type RepositoryPublicKey struct {
	KeyID string `json:"key_id"`
	Key   string `json:"key"`
}

type OverrideRepositorySecret struct {
	EncryptedValue string `json:"encrypted_value"`
	KeyID          string `json:"key_id"`
}

func (c *GitHubClient) encryptSecretWithSodium(pkBase64, clearText string) (string, error) {
	// adapted from implementation by Sterling Hanenkamp (c) 2022
	// See https://zostay.com/posts/2022/05/04/do-not-use-libsodium-with-go/
	var pkBytes [32]byte
	_, err := base64.StdEncoding.Decode(pkBytes[:], []byte(pkBase64))
	if err != nil {
		return "", fmt.Errorf("public key: %w", err)
	}
	raw := []byte(clearText)
	out := make([]byte, 0, len(raw)+box.Overhead+len(pkBytes))
	encryptedRaw, err := box.SealAnonymous(out, raw, &pkBytes, rand.Reader)
	if err != nil {
		return "", err
	}
	encoded := base64.StdEncoding.EncodeToString(encryptedRaw)
	return encoded, nil
}
