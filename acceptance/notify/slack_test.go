package notify_test

import (
	"testing"

	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/acceptance/notify"
	"github.com/databrickslabs/sandbox/go-libs/fixtures"
)

func TestXxx(t *testing.T) {
	fixtures.LoadDebugEnvIfRunsFromIDE(t, "slack")
	notify.Notification{
		Project: "ucx",
		Cloud:   config.CloudAzure,
		WebHook: fixtures.GetEnvOrSkipTest(t, "TEST_HOOK"),
		RunURL:  "https://github.com/databrickslabs/sandbox",
		Report: ecosystem.TestReport{
			{Name: "test_runtime_backend_incorrect_syntax_handled", Flaky: true, Pass: true},
			{Name: "test_running_real_assessment_job"},
			{Name: "test_skipped", Skip: true},
			{Name: "test_running_real_validate_groups_permissions_job_fails", Flaky: true, Pass: true},
		},
	}.ToSlack()
}
