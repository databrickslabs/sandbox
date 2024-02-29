package llnotes

import (
	"fmt"
	"strings"

	"github.com/databricks/databricks-sdk-go/service/serving"
	"github.com/databrickslabs/sandbox/go-libs/sed"
)

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

func (h History) messageTokens(m message) int {
	// this is good enough approximation of message token count
	content := m.ChatMessage().Content
	return len(strings.Split(content, " "))
}

func (h History) totalTokens() int {
	totalTokens := 0
	for _, m := range h {
		totalTokens += h.messageTokens(m)
	}
	return totalTokens
}

func (h History) With(m message) History {
	maxContextSize := 32768 - 2000
	increment := h.messageTokens(m)
	// prompt token count ... cannot equal or exceed 32768
	for (h.totalTokens() + increment) > maxContextSize {
		// discard the e
		copied := History{h[0]}      // a system message, right?...
		h = append(copied, h[3:]...) // skip two messages
	}
	return append(h, m)
}

func (h History) Last() string {
	return h[len(h)-1].ChatMessage().Content
}

func (h History) Excerpt(n int) string {
	var out []string
	oneLine := sed.Rule(`\n|\s+`, ` `)
	for i, v := range h {
		m := v.ChatMessage()
		out = append(out, fmt.Sprintf("(%d/%d) %s: %s",
			i+1, len(h),
			strings.ToUpper(m.Role.String()),
			h.onlyNBytes(oneLine.Apply(m.Content), n)))
	}
	return strings.Join(out, "\n")
}

func (h History) onlyNBytes(j string, numBytes int) string {
	diff := len([]byte(j)) - numBytes
	if diff > 0 {
		return fmt.Sprintf("%s... (%d more bytes)", j[:numBytes], diff)
	}
	return j
}
