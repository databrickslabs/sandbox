package llnotes

import (
	"context"
	"fmt"
	"net/http"

	"github.com/databricks/databricks-sdk-go/client"
)

type Role string

const RoleSystem Role = `system`
const RoleUser Role = `user`
const RoleAssistant Role = `assistant`

type ChatMessage struct {
	Role    Role   `json:"role,omitempty"`
	Content string `json:"content"`
}

type Invocation struct {
	Model string `json:"-"`

	// prompt mode
	Prompt []string `json:"prompt,omitempty"`

	// chat mode
	Messages []ChatMessage `json:"messages,omitempty"`

	// The maximum number of tokens to generate.
	// Integer greater than zero or nil, which represents infinity
	MaxTokens int `json:"max_tokens,omitempty"`

	// Whether to stream the response as it is generated.
	Stream bool `json:"stream,omitempty"`

	// The sampling temperature. 0 is deterministic and higher
	// values introduce more randomness. Float in [0,2]
	Temperature float32 `json:"temperature,omitempty"`

	// The probability threshold used for nucleus sampling.
	// Float in (0,1]
	TopP float32 `json:"top_p,omitempty"`

	// Defines the number of k most likely tokens to use for
	// top-k-filtering. Set this value to 1 to make outputs
	// deterministic.
	//
	// Integer greater than zero or nil, which represents infinity
	TopK int `json:"top_k,omitempty"`

	// Model stops generating further tokens when any one of
	// the sequences in stop is encountered.
	Stop []string `json:"stop,omitempty"`

	// Model stops generating further tokens when any one of
	// the sequences in stop is encountered.
	ErrorBehavior ErrorBehavior `json:"error_behavior,omitempty"`

	// A string that is appended to the end of every completion.
	Suffix string `json:"suffix,omitempty"`

	// Returns the prompt along with the completion.
	Echo bool `json:"echo,omitempty"`

	// If true, pass the prompt directly into the model without
	// any transformation.
	UseRawPrompt bool `json:"use_raw_prompt,omitempty"`
}

type ChatCompletion struct {
	Index int `json:"index"`

	// A chat completion message returned by the model.
	// The role will be assistant.
	Message *ChatMessage `json:"message,omitempty"`

	// A chat completion message part of generated streamed
	// responses from the model. Only the first chunk is guaranteed
	// to have role populated.
	Delta *ChatMessage `json:"delta,omitempty"`

	// The reason the model stopped generating tokens. Only the last
	// chunk will have this populated.
	FinishReason string `json:"finish_reason"`
}

type ObjectType string

const ObjectTypeChatCompletion ObjectType = `chat.completions`
const ObjectTypeChatCompletionChunk ObjectType = `chat.completions.chunk`
const ObjectTypeTextCompletion ObjectType = `text_completion`

type Usage struct {
	CompletionTokens int `json:"completion_tokens"`
	PromptTokens     int `json:"prompt_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

type ErrorBehavior string

const ErrorBehaviorTruncate ErrorBehavior = `truncate`
const ErrorBehaviorError ErrorBehavior = `error`

type InvocationResponse struct {
	ID      string             `json:"id"`
	Choices []CompletionChoice `json:"choices"`
	Object  ObjectType         `json:"object"`
	Created int                `json:"created"`
	Model   string             `json:"model"`
	Usage   *Usage             `json:"usage"`
}

type CompletionChoice struct {
	Index int `json:"index"`

	// The generated completion.
	Text string `json:"text"`

	// A chat completion message returned by the model.
	// The role will be assistant.
	Message *ChatMessage `json:"message,omitempty"`

	// A chat completion message part of generated streamed
	// responses from the model. Only the first chunk is guaranteed
	// to have role populated.
	Delta *ChatMessage `json:"delta,omitempty"`

	// The reason the model stopped generating tokens. Only the last
	// chunk will have this populated.
	FinishReason string `json:"finish_reason"`
}

type FoundationModelAPI struct {
	client *client.DatabricksClient
}

func (a *FoundationModelAPI) Invoke(ctx context.Context, request Invocation) (*InvocationResponse, error) {
	var res InvocationResponse
	path := fmt.Sprintf("/serving-endpoints/%s/invocations", request.Model)
	headers := make(map[string]string)
	headers["Accept"] = "application/json"
	headers["Content-Type"] = "application/json"
	err := a.client.Do(ctx, http.MethodPost, path, headers, request, &res)
	return &res, err
}

