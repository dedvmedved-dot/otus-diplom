package collectors

import (
	"context"
	"testing"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

func TestListWithContinueFullCycle(t *testing.T) {
	// Simulate 3 pages of 200 + a final short page; cap 500.
	// listWithContinue must page through, stop at cap, and never exceed it.
	page := func(i int) []string {
		out := make([]string, 0, 200)
		for j := 0; j < 200; j++ {
			out = append(out, string(rune('a'+i))+string(rune('a'+j%26)))
		}
		return out
	}
	call := 0
	items, truncated, err := listWithContinue(context.Background(), 200, 500, func(opts metav1.ListOptions) ([]string, string, error) {
		call++
		switch call {
		case 1:
			return page(0), "cont-1", nil
		case 2:
			return page(1), "cont-2", nil
		case 3:
			return page(2), "", nil
		}
		return []string{"tail"}, "", nil
	})
	if err != nil {
		t.Fatalf("err: %v", err)
	}
	if len(items) != 500 {
		t.Fatalf("expected 500 items (cap), got %d", len(items))
	}
	if !truncated {
		t.Fatal("expected truncated=true (cap hit)")
	}
}

func TestListWithContinueSinglePage(t *testing.T) {
	items, truncated, err := listWithContinue(context.Background(), 200, 500, func(opts metav1.ListOptions) ([]string, string, error) {
		return []string{"a", "b"}, "", nil
	})
	if err != nil || truncated {
		t.Fatalf("err=%v truncated=%v", err, truncated)
	}
	if len(items) != 2 {
		t.Fatalf("expected 2, got %d", len(items))
	}
}

func TestListWithContinueError(t *testing.T) {
	_, truncated, err := listWithContinue(context.Background(), 200, 500, func(opts metav1.ListOptions) ([]string, string, error) {
		return nil, "cont-1", context.Canceled
	})
	if err == nil {
		t.Fatal("expected error")
	}
	if !truncated {
		t.Fatal("expected truncated=true (partial result)")
	}
}
