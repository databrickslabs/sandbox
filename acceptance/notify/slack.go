package notify

import (
	"fmt"
	"strings"

	"github.com/databricks/databricks-sdk-go/config"
	"github.com/databricks/databricks-sdk-go/openapi/code"
	"github.com/databrickslabs/sandbox/acceptance/ecosystem"
	"github.com/databrickslabs/sandbox/go-libs/slack"
)

type Notification struct {
	Project string
	Cloud   config.Cloud
	Report  ecosystem.TestReport
	WebHook string
	RunURL  string
}

var icons = map[config.Cloud]string{
	config.CloudAzure: "https://portal.azure.com/Content/favicon.ico",
	config.CloudAWS:   "https://aws.amazon.com/favicon.ico",
	config.CloudGCP:   "https://cloud.google.com/favicon.ico",
}

func (n Notification) ToSlack() error {
	res := []string{}
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
		// TODO: duration
		res = append(res, fmt.Sprintf("%s %s", v.Icon(), sentence))
	}
	hook := slack.Webhook(n.WebHook)
	return hook.Notify(slack.Message{
		Text:      n.Report.String(),
		UserName:  n.Project,
		IconEmoji: ":facepalm:",
		Attachments: []slack.Attachment{
			{
				AuthorName: string(n.Cloud),
				AuthorIcon: icons[n.Cloud],
				AuthorLink: n.RunURL,
				Footer:     strings.Join(res, "\n"),
			},
		},
	})
}
