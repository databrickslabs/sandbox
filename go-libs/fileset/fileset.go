package fileset

import (
	"context"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/databricks/databricks-sdk-go/logger"
)

type FileSet []File

func (fi FileSet) Root() string {
	if len(fi) == 0 {
		return "."
	}
	return fi[0].Dir()
}

func (fi FileSet) FirstMatch(pathRegex, needleRegex string) *File {
	path := regexp.MustCompile(pathRegex)
	needle := regexp.MustCompile(needleRegex)
	for _, v := range fi {
		if !path.MatchString(v.Absolute) {
			continue
		}
		if v.Match(needle) {
			return &v
		}
	}
	return nil
}

func (fi FileSet) Filter(pathRegex string) (out FileSet) {
	path := regexp.MustCompile(pathRegex)
	for _, v := range fi {
		if !path.MatchString(v.Absolute) {
			continue
		}
		out = append(out, v)
	}
	return out
}

func (fi FileSet) LastUpdated() time.Time {
	last := time.Time{}
	for _, file := range fi {
		info, err := file.Info()
		if err != nil {
			continue
		}
		if info.ModTime().After(last) {
			last = info.ModTime()
		}
	}
	return last
}

func (fi FileSet) FindAll(pathRegex, needleRegex string) (map[File][]string, error) {
	path := regexp.MustCompile(pathRegex)
	needle := regexp.MustCompile(needleRegex)
	all := map[File][]string{}
	for _, v := range fi {
		if !path.MatchString(v.Absolute) {
			continue
		}
		vall, err := v.FindAll(needle)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", v.Relative, err)
		}
		all[v] = vall
	}
	return all, nil
}

func (fi FileSet) Exists(pathRegex, needleRegex string) bool {
	m := fi.FirstMatch(pathRegex, needleRegex)
	return m != nil
}

type File struct {
	fs.DirEntry
	Absolute string
	Relative string
}

func (fi File) Ext(suffix string) bool {
	return strings.HasSuffix(fi.Name(), suffix)
}

func (fi File) Dir() string {
	return path.Dir(fi.Absolute)
}

func (fi File) MustMatch(needle string) bool {
	return fi.Match(regexp.MustCompile(needle))
}

func (fi File) FindAll(needle *regexp.Regexp) (all []string, err error) {
	raw, err := fi.Raw()
	if err != nil {
		logger.Errorf(context.Background(), "read %s: %s", fi.Absolute, err)
		return nil, err
	}
	for _, v := range needle.FindAllStringSubmatch(string(raw), -1) {
		all = append(all, v[1])
	}
	return all, nil
}

func (fi File) Match(needle *regexp.Regexp) bool {
	raw, err := fi.Raw()
	if err != nil {
		logger.Errorf(context.Background(), "read %s: %s", fi.Absolute, err)
		return false
	}
	return needle.Match(raw)
}

func (fi File) Open() (*os.File, error) {
	return os.Open(fi.Absolute)
}

func (fi File) Raw() ([]byte, error) {
	f, err := fi.Open()
	if err != nil {
		return nil, err
	}
	return io.ReadAll(f)
}

func RecursiveChildren(dir string) (found FileSet, err error) {
	queue, err := ReadDir(dir)
	if err != nil {
		return nil, err
	}
	for len(queue) > 0 {
		current := queue[0]
		queue = queue[1:]
		if !current.IsDir() {
			current.Relative = strings.ReplaceAll(current.Absolute, dir+"/", "")
			found = append(found, current)
			continue
		}
		if current.Name() == "vendor" {
			continue
		}
		children, err := ReadDir(current.Absolute)
		if err != nil {
			return nil, err
		}
		queue = append(queue, children...)
	}
	return found, nil
}

func ReadDir(dir string) (queue []File, err error) {
	f, err := os.Open(dir)
	if err != nil {
		return nil, fmt.Errorf("open: %w", err)
	}
	defer f.Close()
	dirs, err := f.ReadDir(-1)
	if err != nil {
		return nil, fmt.Errorf("read dir: %w", err)
	}
	for _, v := range dirs {
		absolute, err := filepath.Abs(path.Join(dir, v.Name()))
		if err != nil {
			return nil, fmt.Errorf("abs: %w", err)
		}
		queue = append(queue, File{v, absolute, ""})
	}
	return
}
