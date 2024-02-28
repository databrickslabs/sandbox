package llnotes

import "github.com/databricks/databricks-sdk-go/service/serving"

type message interface {
	ChatMessage() serving.ChatMessage
}

type SystemMessage string

func (m SystemMessage) ChatMessage() serving.ChatMessage {
	return serving.ChatMessage{
		Role:    serving.ChatMessageRoleSystem,
		Content: string(m),
	}
}

type UserMessage string

func (m UserMessage) ChatMessage() serving.ChatMessage {
	return serving.ChatMessage{
		Role:    serving.ChatMessageRoleUser,
		Content: string(m),
	}
}

type AssistantMessage string

func (m AssistantMessage) ChatMessage() serving.ChatMessage {
	return serving.ChatMessage{
		Role:    serving.ChatMessageRoleAssistant,
		Content: string(m),
	}
}

type History []message

func (h History) Messages() (out []serving.ChatMessage) {
	for _, v := range h {
		out = append(out, v.ChatMessage())
	}
	return
}

func (h History) With(m message) History {
	return append(h, m)
}

func (h History) Last() string {
	return h[len(h)-1].ChatMessage().Content
}
