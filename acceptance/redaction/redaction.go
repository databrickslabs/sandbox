package redaction

import (
	"bufio"
	"io"
	"sort"
	"strings"
)

type pair struct {
	k, v string
}

func New(m map[string]string) (r Redaction) {
	for k, v := range m {
		r = append(r, pair{k, v})
	}
	// otherwise we have things like https://adb-XXXX.YY.CLOUD_ENVdatabricks.net
	sort.Slice(r, func(i, j int) bool {
		return len(r[i].v) > len(r[j].v)
	})
	return
}

type Redaction []pair

func (r Redaction) ReplaceAll(in string) string {
	for _, p := range r {
		in = strings.ReplaceAll(in, p.v, p.k)
	}
	return in
}

// Copy copies from src to dst, redacting secrets based on the state
// based on the Golang's implementation of io.Copy
func (r Redaction) Copy(dst io.Writer, src io.Reader) (written int64, err error) {
	scanner := bufio.NewScanner(src)
	for scanner.Scan() {
		// scan line-by-line, so that there are
		// less risks of a secret spanning multiple lines
		// (unless it's a base64-encoded key)
		line := r.ReplaceAll(string(scanner.Bytes()))
		n, err := dst.Write([]byte(line + "\n"))
		if err != nil {
			return written, err
		}
		written += int64(n)
	}
	return written, err
}
