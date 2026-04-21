package ecosystem

import (
	"context"
	"encoding/json"
	"io"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestReadGoTestEvents(t *testing.T) {
	events := []goTestEvent{
		{Time: time.Now(), Action: "run", Package: "pkg", Test: "TestA"},
		{Time: time.Now(), Action: "output", Package: "pkg", Test: "TestA", Output: "hello\n"},
		{Time: time.Now(), Action: "pass", Package: "pkg", Test: "TestA", Elapsed: 1.0},
	}
	var lines []string
	for _, e := range events {
		raw, err := json.Marshal(e)
		require.NoError(t, err)
		lines = append(lines, string(raw))
	}
	reader := strings.NewReader(strings.Join(lines, "\n"))
	ch := readGoTestEvents(context.Background(), reader)

	var got []goTestEvent
	for e := range ch {
		got = append(got, e)
	}
	assert.Len(t, got, 3)
	assert.Equal(t, "run", got[0].Action)
	assert.Equal(t, "output", got[1].Action)
	assert.Equal(t, "pass", got[2].Action)
}

func TestReadGoTestEvents_InvalidJSON(t *testing.T) {
	reader := strings.NewReader("not json\n")
	ch := readGoTestEvents(context.Background(), reader)

	var got []goTestEvent
	for e := range ch {
		got = append(got, e)
	}
	assert.Empty(t, got)
}

func TestReadGoTestEvents_EmptyInput(t *testing.T) {
	reader := strings.NewReader("")
	ch := readGoTestEvents(context.Background(), reader)

	var got []goTestEvent
	for e := range ch {
		got = append(got, e)
	}
	assert.Empty(t, got)
}

func TestReadGoTestEvents_ClosedPipe(t *testing.T) {
	r, w := io.Pipe()
	w.Close()
	ch := readGoTestEvents(context.Background(), r)

	var got []goTestEvent
	for e := range ch {
		got = append(got, e)
	}
	assert.Empty(t, got)
}

func TestCollectOutput(t *testing.T) {
	events := []goTestEvent{
		{Action: "output", Output: "line1\n"},
		{Action: "run"},
		{Action: "output", Output: "line2\n"},
	}
	out := collectOutput(events)
	assert.Equal(t, "line1\nline2\n", out)
}

func TestCollectOutput_NoOutputEvents(t *testing.T) {
	events := []goTestEvent{
		{Action: "run"},
		{Action: "pass"},
	}
	assert.Equal(t, "", collectOutput(events))
}

func TestCollectOutput_Empty(t *testing.T) {
	assert.Equal(t, "", collectOutput(nil))
}

func TestSummarize(t *testing.T) {
	output := `Error: something went wrong
Test:   TestFoo
other stuff
Error:   another error
Test:   TestBar
`
	result := summarize(output)
	assert.Contains(t, result, "something went wrong")
	assert.Contains(t, result, "another error")
}

func TestSummarize_NoMatch(t *testing.T) {
	assert.Equal(t, "", summarize("just some output"))
}

func TestCollectTestReport_Pass(t *testing.T) {
	ch := make(chan goTestEvent, 10)
	ch <- goTestEvent{Action: "run", Package: "pkg", Test: "TestA"}
	ch <- goTestEvent{Action: "output", Package: "pkg", Test: "TestA", Output: "ok\n"}
	ch <- goTestEvent{Action: "pass", Package: "pkg", Test: "TestA", Elapsed: 1.5, Time: time.Now()}
	close(ch)

	report := collectTestReport(ch)
	assert.Len(t, report, 1)
	assert.True(t, report[0].Pass)
	assert.Equal(t, "TestA", report[0].Name)
	assert.Equal(t, 1.5, report[0].Elapsed)
	assert.Equal(t, "ok\n", report[0].Output)
}

func TestCollectTestReport_Fail(t *testing.T) {
	ch := make(chan goTestEvent, 10)
	ch <- goTestEvent{Action: "run", Package: "pkg", Test: "TestB"}
	ch <- goTestEvent{Action: "output", Package: "pkg", Test: "TestB", Output: "error\n"}
	ch <- goTestEvent{Action: "fail", Package: "pkg", Test: "TestB", Elapsed: 2.0, Time: time.Now()}
	close(ch)

	report := collectTestReport(ch)
	assert.Len(t, report, 1)
	assert.False(t, report[0].Pass)
	assert.False(t, report[0].Skip)
}

func TestCollectTestReport_Skip(t *testing.T) {
	ch := make(chan goTestEvent, 10)
	ch <- goTestEvent{Action: "run", Package: "pkg", Test: "TestC"}
	ch <- goTestEvent{Action: "output", Package: "pkg", Test: "TestC", Output: "skipping\n"}
	ch <- goTestEvent{Action: "skip", Package: "pkg", Test: "TestC", Elapsed: 0.01, Time: time.Now()}
	close(ch)

	report := collectTestReport(ch)
	assert.Len(t, report, 1)
	assert.True(t, report[0].Skip)
	assert.False(t, report[0].Pass)
}

func TestCollectTestReport_IgnoresPackageLevelEvents(t *testing.T) {
	ch := make(chan goTestEvent, 10)
	// Package-level events have no Test field
	ch <- goTestEvent{Action: "pass", Package: "pkg", Test: ""}
	ch <- goTestEvent{Action: "run", Package: "pkg", Test: "TestA"}
	ch <- goTestEvent{Action: "pass", Package: "pkg", Test: "TestA", Elapsed: 1.0, Time: time.Now()}
	close(ch)

	report := collectTestReport(ch)
	assert.Len(t, report, 1)
	assert.Equal(t, "TestA", report[0].Name)
}

func TestCollectTestReport_UnfinishedTest(t *testing.T) {
	ch := make(chan goTestEvent, 10)
	ch <- goTestEvent{Action: "run", Package: "pkg", Test: "TestHung"}
	ch <- goTestEvent{Action: "output", Package: "pkg", Test: "TestHung", Output: "running...\n"}
	// No pass/fail/skip - simulates a timeout
	close(ch)

	report := collectTestReport(ch)
	assert.Len(t, report, 1)
	assert.False(t, report[0].Pass)
	assert.False(t, report[0].Skip)
	assert.Equal(t, "TestHung", report[0].Name)
}

func TestCollectTestReport_MultipleTests(t *testing.T) {
	ch := make(chan goTestEvent, 20)
	ch <- goTestEvent{Action: "run", Package: "pkg", Test: "TestA"}
	ch <- goTestEvent{Action: "run", Package: "pkg", Test: "TestB"}
	ch <- goTestEvent{Action: "output", Package: "pkg", Test: "TestA", Output: "a\n"}
	ch <- goTestEvent{Action: "output", Package: "pkg", Test: "TestB", Output: "b\n"}
	ch <- goTestEvent{Action: "pass", Package: "pkg", Test: "TestA", Elapsed: 1.0, Time: time.Now()}
	ch <- goTestEvent{Action: "fail", Package: "pkg", Test: "TestB", Elapsed: 2.0, Time: time.Now()}
	close(ch)

	report := collectTestReport(ch)
	assert.Len(t, report, 2)
}

func TestCollectTestReport_Empty(t *testing.T) {
	ch := make(chan goTestEvent)
	close(ch)
	report := collectTestReport(ch)
	assert.Empty(t, report)
}
