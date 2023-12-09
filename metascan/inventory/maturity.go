package inventory

import "strings"

type Maturity int

const (
	Experiment Maturity = iota
	Demo
	Accelerator
	Alpha
	Beta
)

func (m Maturity) String() string {
	return strings.Split("Experiment,Demo,Accelerator,Alpha,Beta", ",")[m]
}
