package sed

import "regexp"

func Rule(regex, replace string) *rule {
	return &rule{regexp.MustCompile(regex), replace}
}

type rule struct {
	regex   *regexp.Regexp
	replace string
}

func (r *rule) Apply(src string) string {
	return r.regex.ReplaceAllString(src, r.replace)
}

type Pipeline []*rule

func (r Pipeline) Apply(src string) string {
	for _, v := range r {
		src = v.Apply(src)
	}
	return src
}
