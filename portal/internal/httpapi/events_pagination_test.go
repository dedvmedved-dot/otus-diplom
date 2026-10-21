package httpapi

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/auth"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/store"
)

func TestEventsCursorRoundTripRFC3339(t *testing.T) {
	// RFC3339 since contains ':' — the JSON cursor must round-trip it safely.
	since := "2026-10-21T07:30:00Z"
	c := encodeEventsCursor("snap123", "portal", since, "warning", "memory-fallback", 42)
	p, err := decodeEventsCursor(c)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	if p.SnapshotID != "snap123" || p.Namespace != "portal" || p.Since != since ||
		p.Severity != "warning" || p.Backend != "memory-fallback" || p.Offset != 42 {
		t.Fatalf("round-trip mismatch: %+v", p)
	}
}

type failStore struct{ mockStore }

func (failStore) ListEvents(ctx context.Context, since *time.Time, severity, namespace string, limit, offset int) ([]store.EventRow, error) {
	return nil, context.DeadlineExceeded
}

func TestEventsMemoryFallbackSecondPage(t *testing.T) {
	now := time.Now().UTC()
	events := make([]model.TimelineEvent, 0, 250)
	for i := 0; i < 250; i++ {
		st := now.Add(-time.Duration(i) * time.Minute).Format(time.RFC3339)
		events = append(events, model.TimelineEvent{
			ID: "e" + string(rune('a'+i%26)) + string(rune('a'+(i/26)%26)),
			Source: "kubernetes", SourceTime: &st, Severity: "normal", ReasonCode: "x",
			OccurrenceCount: 1, Message: "event",
		})
	}
	snap := &collectors.Snapshot{CollectedAt: now, Events: events}
	sum := sha256.Sum256([]byte("test-password"))
	verifier, _ := auth.NewVerifier("portal-operator", hex.EncodeToString(sum[:]))
	s := &Server{collector: mockSnapshotProvider{snap}, store: failStore{}, verifier: verifier,
		cfg: &config.Config{SourceRevision: strings.Repeat("a", 40)}, rate: newTokenBucket(1000), sem: make(chan struct{}, 20)}
	h := s.Handler()

	// Page 1
	req := httptest.NewRequest(http.MethodGet, "/api/v1/events?limit=200&since=1970-01-01T00:00:00Z", nil)
	req.SetBasicAuth("portal-operator", "test-password")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Fatalf("page1: %d", rr.Code)
	}
	var p1 map[string]any
	json.Unmarshal(rr.Body.Bytes(), &p1)
	items := p1["data"].(map[string]any)["items"].([]any)
	if len(items) != 200 {
		t.Fatalf("page1: expected 200 items, got %d", len(items))
	}
	next := p1["nextCursor"].(string)
	if next == "" {
		t.Fatal("page1: expected nextCursor")
	}

	// Page 2 with cursor
	req2 := httptest.NewRequest(http.MethodGet, "/api/v1/events?limit=200&since=1970-01-01T00:00:00Z&cursor="+next, nil)
	req2.SetBasicAuth("portal-operator", "test-password")
	rr2 := httptest.NewRecorder()
	h.ServeHTTP(rr2, req2)
	if rr2.Code != http.StatusOK {
		t.Fatalf("page2: %d", rr2.Code)
	}
	var p2 map[string]any
	json.Unmarshal(rr2.Body.Bytes(), &p2)
	items2 := p2["data"].(map[string]any)["items"].([]any)
	if len(items2) != 50 {
		t.Fatalf("page2: expected 50 items, got %d", len(items2))
	}
	_ = strings.TrimSpace
}
