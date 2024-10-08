package ecosystem

import (
	"encoding/json"
	"fmt"
	"os"
	"path"
	"strings"
	"time"
)

type TestResult struct {
	Time    time.Time `json:"ts"` // encodes as an RFC3339-format string
	Project string    `json:"project"`
	Package string    `json:"package"`
	Name    string    `json:"name"`
	Pass    bool      `json:"pass"`
	Skip    bool      `json:"skip"`
	Flaky   bool      `json:"flaky"`
	Output  string    `json:"output"`
	Elapsed float64   `json:"elapsed"`
}

func (tr TestResult) Duration() time.Duration {
	return time.Duration(tr.Elapsed * float64(time.Second))
}

func (tr TestResult) Failed() bool {
	return !tr.Pass && !tr.Skip
}

func (tr TestResult) Summary(cap int) string {
	out, padding := tr.Output, 512
	diff := len(out) + padding - cap
	if diff > 0 {
		out = fmt.Sprintf("... (skipped %d bytes)\n%s", diff, out[diff:])
	}
	res := []string{}
	res = append(res, "<details>")
	res = append(res, fmt.Sprintf("<summary>%s</summary>", tr))
	res = append(res, fmt.Sprintf("\n```\n%s\n```\n", out))
	res = append(res, "</details>")
	return strings.Join(res, "\n")
}

func (tr TestResult) String() string {
	summary := ""
	if !tr.Pass {
		header, _, ok := strings.Cut(tr.Output, "\n")
		if ok {
			summary = fmt.Sprintf(": %s", header)
		}
	}
	return fmt.Sprintf("%s %s%s (%s)",
		tr.Icon(), tr.Name, summary,
		tr.Duration().Round(time.Millisecond))
}

func (tr TestResult) Icon() string {
	if tr.Skip {
		return "⏭️"
	}
	if tr.Flaky {
		return "🤪"
	}
	if !tr.Pass {
		return "❌"
	}
	return "✅"
}

type TestReport []TestResult

func (r TestReport) Total() time.Duration {
	var elapsed time.Duration
	for _, v := range r {
		elapsed += v.Duration()
	}
	return elapsed
}

func (r TestReport) Pass() bool {
	var passed, run int
	for _, v := range r {
		if v.Skip {
			continue
		}
		if v.Pass {
			passed++
		}
		run++
	}
	if run == 0 {
		return false
	}
	return passed == run
}

func (r TestReport) Flaky() bool {
	for _, v := range r {
		if v.Flaky {
			return true
		}
	}
	return false
}

func (r TestReport) Failed() error {
	if r.Pass() {
		return nil
	}
	return fmt.Errorf(r.String())
}

func (r TestReport) String() string {
	var passed, failed, flaky, run, skipped int
	for _, v := range r {
		if v.Skip {
			skipped++
			continue
		}
		run++
		if v.Flaky {
			flaky++
		}
		if v.Pass {
			passed++
			continue
		}
		failed++
	}
	emoji := "❌"
	if len(r) == 0 {
		return fmt.Sprintf("%s no tests were run", emoji)
	}
	if r.Pass() {
		emoji = "✅"
	}
	var parts []string
	if passed > 0 {
		parts = append(parts, fmt.Sprintf("%d/%d passed", passed, run))
	}
	if flaky > 0 {
		parts = append(parts, fmt.Sprintf("%d flaky", flaky))
	}
	if failed > 0 {
		parts = append(parts, fmt.Sprintf("%d failed", failed))
	}
	if skipped > 0 {
		parts = append(parts, fmt.Sprintf("%d skipped", skipped))
	}
	parts = append(parts, fmt.Sprintf("%s total", r.Total().Round(time.Second)))
	return fmt.Sprintf("%s %s", emoji, strings.Join(parts, ", "))
}

const CommentMaxSize = 65536

func (r TestReport) StepSummary() string {
	res, failures, maybeOutput, padding := []string{r.String()}, []TestResult{}, 0, 1024
	for _, v := range r {
		if !v.Failed() {
			continue
		}
		failures = append(failures, v)
		maybeOutput += len(v.Summary(CommentMaxSize))
	}
	summaryCap := CommentMaxSize - len(strings.Join(res, "\n")) - padding
	if maybeOutput > (CommentMaxSize - padding) {
		// if the output is too large, truncate the summaries up to a fraction of the total size
		summaryCap /= len(failures)
	}
	for _, v := range failures {
		res = append(res, v.Summary(summaryCap))
	}
	if r.Flaky() {
		res = append(res, "\nFlaky tests:\n")
		for _, v := range r {
			if !v.Flaky {
				continue
			}
			res = append(res, fmt.Sprintf(" - %s", v))
		}
	}
	return strings.Join(res, "\n")
}

func (r TestReport) WriteReport(project, dst string) error {
	parent := path.Dir(dst)
	if _, err := os.Stat(parent); os.IsNotExist(err) {
		err = os.MkdirAll(parent, 0755)
		if err != nil {
			return err
		}
	}
	f, err := os.OpenFile(dst, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0755)
	if err != nil {
		return err
	}
	for _, v := range r {
		v.Project = project
		raw, err := json.Marshal(v)
		if err != nil {
			return err
		}
		f.Write(raw)
		f.WriteString("\n")
	}
	return f.Close()
}
