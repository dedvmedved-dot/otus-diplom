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
	c := encodeEventsCursor("snap123", "portal", since, "warning", "memory-fallback", 42, 0)
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

func (failStore) ListEvents(ctx context.Context, since *time.Time, severity, namespace string, limit int, afterID int64) ([]store.EventRow, error) {
	return nil, context.DeadlineExceeded
}

func TestEventsMemoryFallbackSecondPage(t *testing.T) {
	now := time.Now().UTC()
	events := make([]model.TimelineEvent, 0, 250)
	for i := 0; i < 250; i++ {
		st := now.Add(-time.Duration(i) * time.Minute).Format(time.RFC3339)
		events = append(events, model.TimelineEvent{
			ID:     "e" + string(rune('a'+i%26)) + string(rune('a'+(i/26)%26)),
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

type changingStore struct {
	mockStore
	rows   []store.EventRow
	failed bool
	limits []int
}

func (m *changingStore) ListEvents(_ context.Context, _ *time.Time, _, _ string, limit int, _ int64) ([]store.EventRow, error) {
	m.limits = append(m.limits, limit)
	if m.failed {
		return nil, context.DeadlineExceeded
	}
	return append([]store.EventRow(nil), m.rows...), nil
}
func TestEventViewStableAcrossInsertUpdatePrune(t *testing.T) {
	srv := contractTestServer()
	now := time.Now()
	st := &changingStore{}
	for _, id := range []string{"c", "b", "a"} {
		st.rows = append(st.rows, store.EventRow{ID: id, Source: "kubernetes", Severity: "normal", IngestedAt: now, Occurrences: 1, Message: "before", ReasonCode: "Fixture"})
	}
	srv.store = st
	code, first := doGet(t, srv.Handler(), "/api/v1/events?limit=2&severity=normal")
	if code != 200 {
		t.Fatal(code)
	}
	cursor := first["nextCursor"].(string)
	// Simulate concurrent insert, deletion, and update of an unread matching row.
	st.rows = []store.EventRow{{ID: "new", Source: "kubernetes", Severity: "normal", IngestedAt: now}, {ID: "a", Source: "kubernetes", Severity: "critical", Message: "after"}}
	code, second := doGet(t, srv.Handler(), "/api/v1/events?limit=2&severity=normal&cursor="+cursor)
	if code != 200 {
		t.Fatal(code)
	}
	items := second["data"].(map[string]any)["items"].([]any)
	if len(items) != 1 || items[0].(map[string]any)["id"] != "a" || items[0].(map[string]any)["message"] != "before" {
		t.Fatalf("unstable view: %v", items)
	}
	if st.limits[0] != 501 || st.limits[1] != 1 {
		t.Fatal("view creation/probe not bounded")
	}
	code, _ = doGet(t, srv.Handler(), "/api/v1/events?limit=2&severity=warning&cursor="+cursor)
	if code != 400 {
		t.Fatal("filter mismatch accepted")
	}
	st.failed = true
	code, body := doGet(t, srv.Handler(), "/api/v1/events?limit=2&severity=normal&cursor="+cursor)
	if code != 400 || body["code"] != "CURSOR_EXPIRED" {
		t.Fatal("backend switch accepted")
	}
}
func TestEventViewEvictionAndCap(t *testing.T) {
	srv := contractTestServer()
	st := &changingStore{}
	now := time.Now()
	for i := 0; i < 501; i++ {
		st.rows = append(st.rows, store.EventRow{ID: strings.Repeat("a", i%10+1), IngestedAt: now, Source: "kubernetes", Severity: "normal", Occurrences: 1, ReasonCode: "Fixture", Message: "fixture"})
	}
	srv.store = st
	_, first := doGet(t, srv.Handler(), "/api/v1/events?limit=200")
	if first["partial"] != true {
		t.Fatal("bounded database view must disclose truncation")
	}
	cursor := first["nextCursor"].(string)
	for i := 0; i < 33; i++ {
		doGet(t, srv.Handler(), "/api/v1/events?limit=200")
	}
	if len(srv.eventViews) != 32 {
		t.Fatal("view cache unbounded")
	}
	code, body := doGet(t, srv.Handler(), "/api/v1/events?limit=200&cursor="+cursor)
	if code != 400 || body["code"] != "CURSOR_EXPIRED" {
		t.Fatal("evicted view silently changed")
	}
}

func TestEventsSnapshotCapturedOnceIncludingError(t *testing.T) {
	for _, query := range []string{"?limit=1", "?unknown=x"} {
		t.Run(query, func(t *testing.T) {
			now := time.Now().UTC()
			a := &collectors.Snapshot{CollectedAt: now, Events: []model.TimelineEvent{{ID: "a", Source: "portal-status", Severity: "normal", ReasonCode: "Fixture", Message: "A", OccurrenceCount: 1}, {ID: "b", Source: "portal-status", Severity: "normal", ReasonCode: "Fixture", Message: "B", OccurrenceCount: 1}}}
			provider := &swappingProvider{snapA: a, snapB: &collectors.Snapshot{CollectedAt: now.Add(time.Minute)}}
			srv := contractTestServer()
			srv.collector = provider
			srv.store = failStore{}
			code, body := doGet(t, srv.Handler(), "/api/v1/events"+query)
			if provider.Calls() != 1 {
				t.Fatal("snapshot re-read during events request")
			}
			if query == "?limit=1" {
				if code != 200 || body["observedAt"] != now.Format(time.RFC3339) {
					t.Fatal("mixed snapshot")
				}
				cp, err := decodeEventsCursor(body["nextCursor"].(string))
				if err != nil || cp.SnapshotID != snapshotIDFor(a) {
					t.Fatal("mixed cursor")
				}
			} else if code != 400 {
				t.Fatal("invalid query accepted")
			}
		})
	}
}
