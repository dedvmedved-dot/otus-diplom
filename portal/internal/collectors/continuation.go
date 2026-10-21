package collectors

import (
	"context"
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// listWithContinue pages through a Kubernetes List using the Continue token
// until the cap is reached or there are no more pages. Returns the accumulated
// items (never exceeding cap), whether the result is truncated (a continue
// token remains or the cap was hit), and any error. pageSize <= cap.
func listWithContinue[T any](ctx context.Context, pageSize, cap int, listFn func(opts metav1.ListOptions) (items []T, cont string, err error)) ([]T, bool, error) {
	out := make([]T, 0, pageSize)
	opts := metav1.ListOptions{Limit: int64(pageSize)}
	seen := map[string]bool{}
	for {
		if err := ctx.Err(); err != nil {
			return out, true, err
		}
		items, cont, err := listFn(opts)
		if err != nil {
			return out, cont != "", err
		}
		room := cap - len(out)
		if len(items) > room {
			out = append(out, items[:room]...)
			return out, true, nil
		}
		out = append(out, items...)
		if cont == "" {
			return out, false, nil
		}
		if len(out) >= cap {
			return out, true, nil
		}
		if seen[cont] {
			return out, true, fmt.Errorf("repeated continuation token")
		}
		seen[cont] = true
		opts.Continue = cont
	}
}
