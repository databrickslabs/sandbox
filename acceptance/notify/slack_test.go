package notify_test

import (
	"testing"

	"github.com/databricks/databricks-sdk-go/common/environment"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/acceptance/notify"
	"github.com/databrickslabs/sandbox/go-libs/fixtures"
	"github.com/databrickslabs/sandbox/go-libs/slack"
)

func TestMessageDryRun(t *testing.T) {
	fixtures.LoadDebugEnvIfRunsFromIDE(t, "slack")
	hook := fixtures.GetEnvOrSkipTest(t, "TEST_HOOK")
	notify.Notification{
		Project: "ucx",
		Cloud:   environment.CloudAzure,
		RunName: "acceptance #213123",
		RunURL:  "https://github.com/databrickslabs/sandbox",
		Report: ecosystem.TestReport{
			{Name: "test_runtime_backend_incorrect_syntax_handled", Flaky: true, Pass: true, Elapsed: 3.13425},
			{Name: "test_running_real_assessment_job", Elapsed: 392.13425},
			{Name: "test_skipped", Skip: true, Elapsed: 8},
			{Name: "test_running_real_validate_groups_permissions_job_fails", Flaky: true, Pass: true, Elapsed: 812.237889},
		},
	}.ToSlack(slack.Webhook(hook))
}
