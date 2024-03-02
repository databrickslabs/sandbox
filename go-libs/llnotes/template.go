package llnotes

import (
	"bytes"
	"text/template"
)

func MessageTemplate(tmpl string) *messageTemplate {
	t, err := template.New("message").Parse(tmpl)
	if err != nil {
		panic(err)
	}
	return &messageTemplate{t}
}

type messageTemplate struct {
	tmpl *template.Template
}

func (mt *messageTemplate) exec(v any) (*bytes.Buffer, error) {
	var buf bytes.Buffer
	err := mt.tmpl.Execute(&buf, v)
	if err != nil {
		return nil, err
	}
	return &buf, nil
}

func (mt *messageTemplate) AsSystem(v any) message {
	buf, err := mt.exec(v)
	if err != nil {
		panic(err)
	}
	return SystemMessage(buf.String())
}

func (mt *messageTemplate) AsUser(v any) message {
	buf, err := mt.exec(v)
	if err != nil {
		panic(err)
	}
	return SystemMessage(buf.String())
}
