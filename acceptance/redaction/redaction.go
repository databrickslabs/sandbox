package redaction

import (
	"io"
	"strings"
)

type Redaction map[string]string

// Copy copies from src to dst, redacting secrets based on the state
// based on the Golang's implementation of io.Copy
func (r Redaction) Copy(dst io.Writer, src io.Reader) (written int64, err error) {
	buf := make([]byte, 32*1024) // 32KB buffer
	for {
		nr, er := src.Read(buf)
		if nr > 0 {
			// TODO: we can only read into bytes.Buffer and perform replacements there.
			// FXIME: streaming io.Copy has a risk of secret being on the boundary of chunks.
			data := buf[:nr]
			for key, secret := range r {
				data = []byte(strings.ReplaceAll(string(data), secret, key))
			}
			nw, ew := dst.Write(data)
			if nw > 0 {
				written += int64(nw)
			}
			if ew != nil {
				err = ew
				break
			}
			if nr != nw {
				err = io.ErrShortWrite
				break
			}
		}
		if er == io.EOF {
			break
		}
		if er != nil {
			err = er
			break
		}
	}
	return written, err
}
