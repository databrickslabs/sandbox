package ecosystem

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestTestResult_Duration(t *testing.T) {
	tr := TestResult{Elapsed: 1.5}
	assert.Equal(t, 1500*time.Millisecond, tr.Duration())
}

func TestTestResult_Duration_Zero(t *testing.T) {
	tr := TestResult{}
	assert.Equal(t, time.Duration(0), tr.Duration())
}

func TestTestResult_Failed(t *testing.T) {
	tests := []struct {
		name   string
		result TestResult
		want   bool
	}{
		{"pass", TestResult{Pass: true}, false},
		{"skip", TestResult{Skip: true}, false},
		{"fail", TestResult{Pass: false, Skip: false}, true},
		{"pass and skip", TestResult{Pass: true, Skip: true}, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, tt.result.Failed())
		})
	}
}

func TestTestResult_Icon(t *testing.T) {
	tests := []struct {
		name   string
		result TestResult
		want   string
	}{
		{"pass", TestResult{Pass: true}, "✅"},
		{"fail", TestResult{}, "❌"},
		{"skip", TestResult{Skip: true}, "⏭️"},
		{"flaky", TestResult{Flaky: true}, "🤪"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, tt.result.Icon())
		})
	}
}

func TestTestResult_String_Pass(t *testing.T) {
	tr := TestResult{Name: "TestFoo", Pass: true, Elapsed: 2.5}
	s := tr.String()
	assert.Contains(t, s, "✅")
	assert.Contains(t, s, "TestFoo")
	assert.Contains(t, s, "2.5s")
}

func TestTestResult_String_Fail(t *testing.T) {
	tr := TestResult{Name: "TestBar", Pass: false, Output: "first line\nsecond line", Elapsed: 0.123}
	s := tr.String()
	assert.Contains(t, s, "❌")
	assert.Contains(t, s, "TestBar")
	assert.Contains(t, s, "first line")
}

func TestTestResult_Summary(t *testing.T) {
	tr := TestResult{Name: "TestFoo", Pass: false, Output: "some output", Elapsed: 1.0}
	s := tr.Summary(CommentMaxSize)
	assert.Contains(t, s, "<details>")
	assert.Contains(t, s, "</details>")
	assert.Contains(t, s, "<summary>")
	assert.Contains(t, s, "some output")
}

func TestTestResult_Summary_Truncates(t *testing.T) {
	longOutput := strings.Repeat("x", 2000)
	tr := TestResult{Name: "TestFoo", Pass: false, Output: longOutput, Elapsed: 1.0}
	s := tr.Summary(1000)
	assert.Contains(t, s, "skipped")
}

func TestTestReport_Total(t *testing.T) {
	r := TestReport{
		{Elapsed: 1.0},
		{Elapsed: 2.5},
		{Elapsed: 0.5},
	}
	assert.Equal(t, 4*time.Second, r.Total())
}

func TestTestReport_Total_Empty(t *testing.T) {
	r := TestReport{}
	assert.Equal(t, time.Duration(0), r.Total())
}

func TestTestReport_Pass(t *testing.T) {
	tests := []struct {
		name   string
		report TestReport
		want   bool
	}{
		{"all pass", TestReport{{Pass: true}, {Pass: true}}, true},
		{"one fail", TestReport{{Pass: true}, {Pass: false}}, false},
		{"empty", TestReport{}, false},
		{"all skip", TestReport{{Skip: true}, {Skip: true}}, false},
		{"pass with skip", TestReport{{Pass: true}, {Skip: true}}, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, tt.report.Pass())
		})
	}
}

func TestTestReport_Flaky(t *testing.T) {
	assert.False(t, TestReport{{Pass: true}}.Flaky())
	assert.True(t, TestReport{{Pass: true, Flaky: true}}.Flaky())
	assert.False(t, TestReport{}.Flaky())
}

func TestTestReport_Failed(t *testing.T) {
	assert.Nil(t, TestReport{{Pass: true}}.Failed())
	assert.Error(t, TestReport{{Pass: false}}.Failed())
	assert.Error(t, TestReport{}.Failed())
}

func TestTestReport_String_AllPass(t *testing.T) {
	r := TestReport{{Pass: true, Elapsed: 1.0}, {Pass: true, Elapsed: 2.0}}
	s := r.String()
	assert.Contains(t, s, "✅")
	assert.Contains(t, s, "2/2 passed")
}

func TestTestReport_String_WithFailures(t *testing.T) {
	r := TestReport{{Pass: true, Elapsed: 1.0}, {Pass: false, Elapsed: 2.0}}
	s := r.String()
	assert.Contains(t, s, "❌")
	assert.Contains(t, s, "1 failed")
	assert.Contains(t, s, "1/2 passed")
}

func TestTestReport_String_Empty(t *testing.T) {
	r := TestReport{}
	s := r.String()
	assert.Contains(t, s, "no tests were run")
}

func TestTestReport_String_WithSkip(t *testing.T) {
	r := TestReport{{Pass: true, Elapsed: 1.0}, {Skip: true}}
	s := r.String()
	assert.Contains(t, s, "1 skipped")
}

func TestTestReport_String_WithFlaky(t *testing.T) {
	r := TestReport{{Pass: true, Flaky: true, Elapsed: 1.0}}
	s := r.String()
	assert.Contains(t, s, "1 flaky")
}

func TestTestReport_StepSummary(t *testing.T) {
	r := TestReport{
		{Name: "TestPass", Pass: true, Elapsed: 1.0},
		{Name: "TestFail", Pass: false, Output: "error happened", Elapsed: 2.0},
	}
	s := r.StepSummary()
	assert.Contains(t, s, "TestFail")
	assert.Contains(t, s, "error happened")
}

func TestTestReport_StepSummary_WithFlaky(t *testing.T) {
	r := TestReport{
		{Name: "TestFlaky", Pass: true, Flaky: true, Elapsed: 1.0},
	}
	s := r.StepSummary()
	assert.Contains(t, s, "Flaky tests")
	assert.Contains(t, s, "TestFlaky")
}

func TestTestReport_WriteReport(t *testing.T) {
	dir := t.TempDir()
	dst := filepath.Join(dir, "sub", "report.json")
	r := TestReport{
		{Name: "TestOne", Pass: true, Package: "pkg1", Elapsed: 1.0},
		{Name: "TestTwo", Pass: false, Package: "pkg2", Elapsed: 2.0},
	}
	err := r.WriteReport("myproject", dst)
	require.NoError(t, err)

	data, err := os.ReadFile(dst)
	require.NoError(t, err)
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	assert.Len(t, lines, 2)
	assert.Contains(t, lines[0], `"project":"myproject"`)
	assert.Contains(t, lines[0], `"name":"TestOne"`)
	assert.Contains(t, lines[1], `"name":"TestTwo"`)
}

func TestTestReport_WriteReport_ExistingDir(t *testing.T) {
	dir := t.TempDir()
	dst := filepath.Join(dir, "report.json")
	r := TestReport{{Name: "TestOne", Pass: true}}
	err := r.WriteReport("proj", dst)
	require.NoError(t, err)
}
