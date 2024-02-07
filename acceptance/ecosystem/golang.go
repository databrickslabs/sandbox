package ecosystem

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/databricks/databricks-sdk-go/logger"
	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/fileset"
	"github.com/databrickslabs/sandbox/go-libs/process"
	"github.com/nxadm/tail"
)

type GoTestRunner struct{}

func (r GoTestRunner) Detect(files fileset.FileSet) bool {
	return files.Exists(`go.mod`, `module .*\n`)
}

func (r GoTestRunner) ListAll(ctx context.Context, files fileset.FileSet) (all []string) {
	found, _ := files.FindAll(`_test.go`, `func (TestAcc\w+)\(t`)
	for _, v := range found {
		all = append(all, v...)
	}
	return all
}

func (r GoTestRunner) RunOne(ctx context.Context, files fileset.FileSet, one string) error {
	found := files.FirstMatch(`_test.go`, fmt.Sprintf(`func %s\(`, one))
	if found == nil {
		return fmt.Errorf("not found: %s", one)
	}
	logger.Infof(ctx, "found test in %s", found.Dir())

	// make sure to sync on writing to stdout
	reader, writer := io.Pipe()
	defer reader.Close()
	defer writer.Close()

	// create temp file to forward logs produced by subprocess of subprocess
	debug, err := os.CreateTemp("/tmp", fmt.Sprintf("debug-%s-*.log", one))
	if err != nil {
		return err
	}
	defer debug.Close()
	defer os.Remove(debug.Name())
	tailer, err := tail.TailFile(debug.Name(), tail.Config{Follow: true})
	if err != nil {
		return err
	}
	go io.CopyBuffer(os.Stdout, reader, make([]byte, 128))
	go func() {
		for line := range tailer.Lines {
			writer.Write([]byte(line.Text + "\n"))
		}
	}()

	return process.Forwarded(ctx, []string{"go", "test", ".", "-v",
		"-coverpkg=./...",
		"-coverprofile=coverage.txt",
		"-timeout=30m",
		"-run", fmt.Sprintf("^%s$", one)},
		reader, writer, os.Stderr,
		process.WithDir(found.Dir()),

		// Terraform debug logging is a bit involved.
		// See https://www.terraform.io/plugin/log/managing
		process.WithEnv("TF_LOG", "DEBUG"),
		process.WithEnv("TF_LOG_SDK", "INFO"),
		process.WithEnv("TF_LOG_PATH", debug.Name()),
	)
}

func (r GoTestRunner) RunAll(ctx context.Context, files fileset.FileSet) (results TestReport, err error) {
	goMod := files.FirstMatch(`go.mod`, `module .*\n`)
	root := files.Root()
	if goMod == nil {
		return nil, fmt.Errorf("%s has no module file", root)
	}
	raw, err := goMod.Raw()
	if err != nil {
		return nil, err
	}
	lines := strings.Split(string(raw), "\n")
	module := strings.Split(lines[0], " ")[1]
	// make sure to sync on writing to stdout
	// See https://github.com/golang/go/issues/10338
	outReader, outWriter, err := os.Pipe()
	if err != nil {
		return nil, err
	}
	errBuf := bytes.NewBuffer([]byte{})
	// otherwise [ERROR] cannot parse JSON line:
	// invalid character 'g' looking for beginning of value -
	// go: downloading github.com/stretchr/testify v1.8.4
	errReader, errWriter, err := os.Pipe()
	if err != nil {
		return nil, err
	}
	// certain environments need to further filter down the set of tests to run,
	// hence the `TEST_FILTER` environment variable (for now) with `TestAcc` as
	// the default prefix.
	testFilter, ok := env.Lookup(ctx, "TEST_FILTER")
	if !ok {
		testFilter = "TestAcc"
	}
	logDir := env.Get(ctx, LogDirEnv)
	openFlags := os.O_CREATE | os.O_TRUNC | os.O_WRONLY
	// Tee into file so we can debug issues with logic below.
	goTestStdout, err := os.OpenFile(filepath.Join(logDir, "go-test.out"), openFlags, 0644)
	if err != nil {
		return nil, fmt.Errorf("go-test.out: %w", err)
	}
	defer goTestStdout.Close()
	// separate tailing for standard error of subprocess, so that the output could be analyzed easier
	goTestStderr, err := os.OpenFile(filepath.Join(logDir, "go-test.err"), openFlags, 0644)
	if err != nil {
		return nil, fmt.Errorf("go-test.err: %w", err)
	}
	defer goTestStderr.Close()
	teeErr := io.TeeReader(errReader, goTestStderr)
	go io.Copy(errBuf, teeErr)
	teeOut := io.TeeReader(outReader, goTestStdout)
	// We have to wait for the output to be fully processed before returning.
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		ch := readGoTestEvents(ctx, teeOut)
		results = collectTestReport(ch)
		// Strip root module from package name for brevity.
		for i := range results {
			results[i].Package = strings.TrimPrefix(results[i].Package, module+"/")
		}
	}()
	// we may later need to add something like  `"-parallel", "20"``, preferably configurable.
	// on GitHub actions we have only a single core available, hence no test parallelism.
	// on the other hand, current way of logging pollutes test log output with another test log output,
	// that may lead to confusion. Hence, on CI it's still better to have no parallelism.
	err = process.Forwarded(ctx, []string{
		"go", "test", "./...", "-json",
		"-timeout", "1h",
		"-coverpkg=./...",
		fmt.Sprintf("-coverprofile=%s/go-coverprofile", logDir),
		"-run", fmt.Sprintf("^%s", testFilter),
	}, nil, outWriter, errWriter, process.WithDir(root))
	// The process has terminated; close the writer it had been writing into.
	outWriter.Close()
	errWriter.Close()
	// Wait for the goroutine above to finish collecting the test report.
	//
	// If c.Stdin is not an *os.File, Wait also waits for the I/O loop
	// copying from c.Stdin into the process's standard input
	// to complete.
	wg.Wait()

	if results.Pass() && err != nil {
		results = append(results, TestResult{
			Time:    time.Now(),
			Package: "<root>",
			Name:    "compile",
			Output:  errBuf.String(),
		})
		return results, err
	}

	return results, nil
}

// goTestEvent is defined at https://pkg.go.dev/cmd/test2json#hdr-Output_Format.
type goTestEvent struct {
	Time    time.Time // encodes as an RFC3339-format string
	Action  string
	Package string
	Test    string
	Elapsed float64 // seconds
	Output  string
}

func readGoTestEvents(ctx context.Context, reader io.Reader) <-chan goTestEvent {
	ch := make(chan goTestEvent)
	go func() {
		defer close(ch)
		scanner := bufio.NewScanner(reader)
		for scanner.Scan() {
			line := scanner.Bytes()

			var testEvent goTestEvent
			err := json.Unmarshal(line, &testEvent)
			if err != nil {
				logger.Errorf(ctx, "cannot parse JSON line: %s - %s", err, string(line))
				return
			}
			ch <- testEvent
		}
		err := scanner.Err()
		if err != nil && err != io.ErrClosedPipe {
			logger.Errorf(ctx, "cannot scan json lines: %s", err)
			return
		}
	}()
	return ch
}

func collectOutput(testEvents []goTestEvent) string {
	var b strings.Builder
	for _, testEvent := range testEvents {
		if testEvent.Action == "output" {
			b.WriteString(testEvent.Output)
		}
	}
	return b.String()
}

func summarize(output string) string {
	var re = regexp.MustCompile(`(?mUs)Error:\s+(.*)Test:\s+`)
	concise := re.FindAllString(output, -1)
	return strings.Join(concise, "\n")
}

func collectTestReport(ch <-chan goTestEvent) (report TestReport) {
	testEventsByKey := map[string][]goTestEvent{}
	for testEvent := range ch {
		if testEvent.Test == "" {
			continue
		}
		// Keep track of all events per test.
		key := fmt.Sprintf("%s/%s", testEvent.Package, testEvent.Test)
		testEventsByKey[key] = append(testEventsByKey[key], testEvent)
		// Only take action on pass/skip/fail
		switch testEvent.Action {
		case "pass":
			testLog := collectOutput(testEventsByKey[key])
			delete(testEventsByKey, key)
			report = append(report, TestResult{
				Time:    testEvent.Time,
				Package: testEvent.Package,
				Name:    testEvent.Test,
				Pass:    true,
				Skip:    false,
				Output:  testLog,
				Elapsed: testEvent.Elapsed,
			})
			log.Printf("[INFO] ✅ %s (%0.3fs)", testEvent.Test, testEvent.Elapsed)
		case "skip":
			testLog := collectOutput(testEventsByKey[key])
			delete(testEventsByKey, key)
			report = append(report, TestResult{
				Time:    testEvent.Time,
				Package: testEvent.Package,
				Name:    testEvent.Test,
				Pass:    false,
				Skip:    true,
				Output:  testLog,
				Elapsed: testEvent.Elapsed,
			})
			log.Printf("[INFO] 🦥 %s: %s", testEvent.Test, testLog)
		case "fail":
			testLog := collectOutput(testEventsByKey[key])
			delete(testEventsByKey, key)
			report = append(report, TestResult{
				Time:    testEvent.Time,
				Package: testEvent.Package,
				Name:    testEvent.Test,
				Pass:    false,
				Skip:    false,
				Output:  testLog,
				Elapsed: testEvent.Elapsed,
			})
			log.Printf("[INFO] ❌ %s (%0.3fs)\n%s", testEvent.Test, testEvent.Elapsed, summarize(testLog))
			// We print the full error logs in case the test fails for easier debugging on github actions
			log.Printf("[INFO][%s] %s", testEvent.Test, testLog)
		default:
			continue
		}
	}
	// Mark remaining tests as failed (timed out?)
	for _, testEvents := range testEventsByKey {
		testEvent := testEvents[len(testEvents)-1]
		testLog := collectOutput(testEvents)
		report = append(report, TestResult{
			Time:    testEvent.Time,
			Package: testEvent.Package,
			Name:    testEvent.Test,
			Pass:    false,
			Skip:    false,
			Output:  testLog,
			Elapsed: testEvent.Elapsed,
		})
		log.Printf("[INFO] ❌ %s (%0.3fs)\n%s", testEvent.Test, testEvent.Elapsed, summarize(testLog))
	}
	return
}
