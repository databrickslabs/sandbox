package slack

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
)

type Message struct {
	Text        string       `json:"text,omitempty"`
	UserName    string       `json:"username,omitempty"`
	IconURL     string       `json:"icon_url,omitempty"`
	IconEmoji   string       `json:"icon_emoji,omitempty"`
	Channel     string       `json:"channel,omitempty"`
	LinkNames   string       `json:"link_names,omitempty"`
	UnfurlLinks bool         `json:"unfurl_links"`
	Attachments []Attachment `json:"attachments,omitempty"`
}

type Attachment struct {
	Fallback   string  `json:"fallback"`
	Pretext    string  `json:"pretext,omitempty"`
	Color      string  `json:"color,omitempty"`
	AuthorName string  `json:"author_name,omitempty"`
	AuthorLink string  `json:"author_link,omitempty"`
	AuthorIcon string  `json:"author_icon,omitempty"`
	Footer     string  `json:"footer,omitempty"`
	Fields     []Field `json:"fields,omitempty"`
}

type Field struct {
	Title string `json:"title,omitempty"`
	Value string `json:"value,omitempty"`

	// displays field in column
	Short bool `json:"short,omitempty"`
}

type Webhook string

func (url Webhook) Notify(msg Message) error {
	raw, err := json.Marshal(msg)
	if err != nil {
		return fmt.Errorf("json: %w", err)
	}
	buf := bytes.NewBuffer(raw)
	response, err := http.Post(string(url), "application/json", buf)
	if err != nil {
		return fmt.Errorf("json: %w", err)
	}
	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("%d %s", response.StatusCode, response.Status)
	}
	return nil
}
