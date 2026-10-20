package collectors

import (
	"context"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// listWithContinue pages through a Kubernetes List using the Continue token
// until the cap is reached or there are no more pages. Returns the accumulated
// items, whether the result is truncated (a continue token remains), and any
// error. pageSize <= cap; the returned slice never exceeds cap.
func listWithContinue[T any](ctx context.Context, pageSize, cap int, listFn func(opts metav1.ListOptions) (items []T, cont string, err error)) ([]T, bool, error) {
	out := make([]T, 0, pageSize)
	opts := metav1.ListOptions{Limit: int64(pageSize)}
	for {
		items, cont, err := listFn(opts)
		if err != nil {
			return out, cont != "", err
		}
		out = append(out, items...)
		if cont == "" || len(out) >= cap {
			return out, cont != "", nil
		}
		opts.Continue = cont
	}
}
