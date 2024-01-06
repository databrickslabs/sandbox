package counters

import "sort"

type Counter[K comparable] map[K]int

func NewStringCounter() Counter[string] {
	return Counter[string]{}
}

func (c Counter[K]) Add(k K) {
	c.AddN(k, 1)
}

func (c Counter[K]) AddN(k K, n int) {
	c[k] += n
}

func (c Counter[K]) Without(without K) Counter[K] {
	out := Counter[K]{}
	for k, v := range c {
		if k == without {
			continue
		}
		out[k] = v
	}
	return out
}

type Pair[K comparable] struct {
	key   K
	count int
}

func (c Counter[K]) Stats() (stats []Pair[K]) {
	for k, v := range c {
		stats = append(stats, Pair[K]{k, v})
	}
	sort.Slice(stats, func(i, j int) bool {
		return stats[i].count > stats[j].count
	})
	return stats
}

func (c Counter[K]) Keys() (out []K) {
	for _, v := range c.Stats() {
		out = append(out, v.key)
	}
	return out
}

func (c Counter[K]) HeadOrDefault(k K) K {
	keys := c.Keys()
	if len(keys) == 0 {
		return k
	}
	return keys[0]
}
