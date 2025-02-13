package notify

import (
	"fmt"
	"strings"
	"time"

	"github.com/databricks/databricks-sdk-go/common/environment"
	"github.com/databricks/databricks-sdk-go/openapi/code"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/go-libs/slack"
)

type Notification struct {
	Project string
	Cloud   environment.Cloud
	RunName string
	Report  ecosystem.TestReport
	RunURL  string
}

var icons = map[environment.Cloud]string{
	environment.CloudAzure: "https://portal.azure.com/Content/favicon.ico",
	environment.CloudAWS:   "https://aws.amazon.com/favicon.ico",
	environment.CloudGCP:   "https://cloud.google.com/favicon.ico",
}

func (n Notification) ToSlack(hook slack.Webhook) error {
	var failures, flakes []string
	for _, v := range n.Report {
		if v.Skip {
			continue
		}
		if v.Pass && !v.Flaky {
			continue
		}
		n := code.Named{Name: v.Name}
		// in order to fit in mobile messages, we normalize the names
		// of tests by tokeinizing them and turning into sentences.
		sentence := n.TrimPrefix("test").TitleName()
		msg := fmt.Sprintf("%s _(%s)_", sentence, v.Duration().Round(time.Second))
		if v.Flaky {
			flakes = append(flakes, msg)
		} else {
			failures = append(failures, msg)
		}
	}
	var fields []slack.Field
	if len(failures) > 0 {
		fields = append(fields, slack.Field{
			Title: fmt.Sprintf("😔 %d failing", len(failures)),
			Value: strings.Join(failures, "\n"),
		})
	}
	if len(flakes) > 0 {
		fields = append(fields, slack.Field{
			Title: fmt.Sprintf("🤪 %d flaky", len(flakes)),
			Value: strings.Join(flakes, "\n"),
		})
	}
	if n.RunName == "" {
		n.RunName = string(n.Cloud)
	}
	return hook.Notify(slack.Message{
		Text:      n.Report.String(),
		UserName:  n.Project,
		IconEmoji: ":facepalm:",
		Attachments: []slack.Attachment{
			{
				AuthorName: n.RunName,
				AuthorIcon: icons[n.Cloud],
				AuthorLink: n.RunURL,
				Fields:     fields,
			},
		},
	})
}
