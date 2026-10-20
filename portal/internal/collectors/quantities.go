package collectors

import (
	"k8s.io/apimachinery/pkg/api/resource"
)

// parseCpuCores parses a Kubernetes CPU quantity into fractional cores.
func parseCpuCores(q string) *float64 {
	if q == "" {
		return nil
	}
	r, err := resource.ParseQuantity(q)
	if err != nil {
		return nil
	}
	v := float64(r.MilliValue()) / 1000.0
	return &v
}

// parseMemoryBytes parses a Kubernetes memory quantity into bytes.
func parseMemoryBytes(q string) *int64 {
	if q == "" {
		return nil
	}
	r, err := resource.ParseQuantity(q)
	if err != nil {
		return nil
	}
	v := r.Value()
	return &v
}

// resourceParseMilli parses a quantity into milli-units.
func resourceParseMilli(s string) (int64, error) {
	q, err := resource.ParseQuantity(s)
	if err != nil {
		return 0, err
	}
	return q.MilliValue(), nil
}

// resourceParseBytes parses a quantity into bytes.
func resourceParseBytes(s string) (int64, error) {
	q, err := resource.ParseQuantity(s)
	if err != nil {
		return 0, err
	}
	return q.Value(), nil
}
