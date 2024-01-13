package main

import "github.com/sethvargo/go-githubactions"

func main() {
	a := githubactions.New()

	a.Debugf("this is debug")
	a.Infof("This is info")
	a.Noticef("This is notice")
	a.Warningf("this is warning")
	a.Errorf("this is error")

	m := map[string]string{
		"file": "app.go",
		"line": "100",
	}
	a.WithFieldsMap(m).Errorf("an error message")

	a.SetOutput("sample", "foo")
}
