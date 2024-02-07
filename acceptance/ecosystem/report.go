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

func (tr TestResult) String() string {
	return fmt.Sprintf("%s %s (%0.3fs)", tr.icon(), tr.Name, tr.Elapsed)
}
func (tr TestResult) icon() string {
	if tr.Skip {
		return "🦥"
	}
	if !tr.Pass {
		return "❌"
	}
	return "✅"
}

type TestReport []TestResult

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
	emoji := "❌"
	if r.Pass() {
		emoji = "✅"
	}
	var parts []string
	if passed > 0 {
		parts = append(parts, fmt.Sprintf("%d/%d passed", passed, run))
	}
	if failed > 0 {
		parts = append(parts, fmt.Sprintf("%d failed", failed))
	}
	if skipped > 0 {
		parts = append(parts, fmt.Sprintf("%d skipped", skipped))
	}
	return fmt.Sprintf("%s %s", emoji, strings.Join(parts, ", "))
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
