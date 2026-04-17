package notify

// Human-readable titles for identifiers (e.g. Go test names) without importing
// github.com/databricks/databricks-sdk-go/openapi/code, which was removed from
// published SDK modules starting at v0.127.0.
//
// The word-splitting and TrimPrefix/TitleName behavior matches the former
// databricks-sdk-go openapi/code.Named implementation (Apache-2.0).

import (
	"strings"
	"unicode"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"
)

var englishTitle = cases.Title(language.English)

type asciiNamed struct {
	Name string
}

func humanizeTestName(name string) string {
	n := asciiNamed{Name: name}
	return n.trimPrefix("test").titleName()
}

func (n *asciiNamed) camelName() string {
	if n.Name == "_" {
		return "_"
	}
	cc := n.pascalName()
	if cc == "" {
		return ""
	}
	return strings.ToLower(cc[0:1]) + cc[1:]
}

func (n *asciiNamed) trimPrefix(prefix string) *asciiNamed {
	return &asciiNamed{
		Name: strings.TrimPrefix(n.camelName(), prefix),
	}
}

func (n *asciiNamed) pascalName() string {
	var sb strings.Builder
	for _, w := range n.splitASCII() {
		sb.WriteString(englishTitle.String(w))
	}
	return sb.String()
}

func (n *asciiNamed) titleName() string {
	return englishTitle.String(strings.Join(n.splitASCII(), " "))
}

func (n *asciiNamed) search(name string, cond func(rune) bool, dir bool, i int) bool {
	nameLen := len(name)
	incr := 1
	if !dir {
		incr = -1
	}
	for j := i; j >= 0 && j < nameLen; j += incr {
		if unicode.IsLetter(rune(name[j])) {
			return cond(rune(name[j]))
		}
	}
	return false
}

func (n *asciiNamed) checkCondAtNearestLetters(name string, cond func(rune) bool, i int) bool {
	r := rune(name[i])

	if unicode.IsLetter(r) {
		return cond(r)
	}
	return n.search(name, cond, true, i) && n.search(name, cond, false, i)
}

func (n *asciiNamed) splitASCII() (w []string) {
	var current []rune
	var name = n.Name
	nameLen := len(name)
	var isPrevUpper, isCurrentUpper, isNextLower, isNextUpper, isNotLastChar bool
	for i := 0; i < nameLen; i++ {
		r := rune(name[i])
		if r == '$' {
			continue
		}
		isCurrentUpper = n.checkCondAtNearestLetters(name, unicode.IsUpper, i)
		r = unicode.ToLower(r)
		isNextLower = false
		isNextUpper = false
		isNotLastChar = i+1 < nameLen
		if isNotLastChar {
			isNextLower = n.checkCondAtNearestLetters(name, unicode.IsLower, i+1)
			isNextUpper = n.checkCondAtNearestLetters(name, unicode.IsUpper, i+1)
		}
		split, before, after := false, false, true
		if isPrevUpper && isCurrentUpper && isNextLower && isNotLastChar {
			split = true
			before = false
			after = true
		}
		if !isCurrentUpper && isNextUpper {
			split = true
			before = true
			after = false
		}
		if !unicode.IsLetter(r) && !unicode.IsNumber(r) {
			split = true
			before = false
			after = false
		}
		if before {
			current = append(current, r)
		}
		if split && len(current) > 0 {
			w = append(w, string(current))
			current = []rune{}
		}
		if after {
			current = append(current, r)
		}
		isPrevUpper = isCurrentUpper
	}
	if len(current) > 0 {
		w = append(w, string(current))
	}
	return w
}
