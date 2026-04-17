package notify

import "testing"

func TestHumanizeTestName(t *testing.T) {
	// Expected strings match databricks-sdk-go@v0.126.0 openapi/code.Named
	// (.TrimPrefix("test").TitleName()) before openapi/code was dropped.
	for _, tc := range []struct {
		in, want string
	}{
		{"TestFooBar", "Foo Bar"},
		{"testFooBar", "Foo Bar"},
		{"TestClustersApiIntegration", "Clusters Api Integration"},
		{"Test_Parse_HTML", "Parse Html"},
		{"parseHTMLNow", "Parse Html Now"},
		{"test_runtime_backend_incorrect_syntax_handled", "Runtime Backend Incorrect Syntax Handled"},
	} {
		t.Run(tc.in, func(t *testing.T) {
			if got := humanizeTestName(tc.in); got != tc.want {
				t.Fatalf("humanizeTestName(%q) = %q; want %q", tc.in, got, tc.want)
			}
		})
	}
}
