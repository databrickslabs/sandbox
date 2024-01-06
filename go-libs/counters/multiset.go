package counters

type Multiset[K,V comparable] map[K]map[V]bool

func (ms Multiset[K, V]) Add(k K, v V) {
	_, ok := ms[k]
	if !ok {
		ms[k] = map[V]bool{}
	}
	
}