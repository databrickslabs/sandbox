package redaction_test

import (
	"testing"

	"github.com/databrickslabs/sandbox/acceptance/redaction"
	"github.com/stretchr/testify/assert"
)

func TestKeyLen(t *testing.T) {
	r := redaction.New(map[string]string{
		"CLOUD_ENV":       "azure",
		"DATABRICKS_HOST": "https://adb-123.45.azuredatabricks.net",
	})

	input := "Running azure tests on https://adb-123.45.azuredatabricks.net host"
	assert.Equal(t, "Running CLOUD_ENV tests on DATABRICKS_HOST host", r.ReplaceAll(input))
}
