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
	Output  string    `json:"output"`
	Elapsed float64   `json:"elapsed"`
}

type TestReport []TestResult

func (r TestReport) Pass() bool {
	for _, v := range r {
		if !v.Pass {
			return false
		}
	}
	return true
}

func (r TestReport) String() string {
	var passed, failed, run, skipped int
	for _, v := range r {
		if v.Skip {
			skipped++
			continue
		}
		run++
		if v.Pass {
			passed++
			continue
		}
		failed++
	}
	result := "❌"
	if passed == run {
		result = "✅"
	}
	return fmt.Sprintf("%s %d/%d passed, %d failed, %d skipped",
		result, passed, run, failed, skipped)
}

func (r TestReport) StepSummary() string {
	if r.Pass() {
		return "# " + r.String()
	}
	res := []string{"# " + r.String()}
	res = append(res, "<table>")
	for _, v := range r {
		if v.Pass || v.Skip {
			continue
		}
		res = append(res, "<tr><td>")
		res = append(res, fmt.Sprintf("❌ %s.%s (%0.3fs)<br/>", v.Package, v.Name, v.Elapsed))
		res = append(res, fmt.Sprintf("<pre><code>%s</code></pre>", v.Output))
		res = append(res, "</td></tr>")
	}
	res = append(res, "</table>")
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
