package redaction

import (
	"bufio"
	"io"
	"strings"
)

type Redaction map[string]string

func (r Redaction) ReplaceAll(in string) string {
	for key, secret := range r {
		in = strings.ReplaceAll(in, secret, key)
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
		n, err := dst.Write([]byte(line))
		if err != nil {
			return written, err
		}
		written += int64(n)
	}
	return written, err
}
