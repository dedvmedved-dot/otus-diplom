package httpapi

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/auth"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

// swappingProvider returns snapA on the FIRST Latest() call and snapB on every
// subsequent call. It simulates the collector swapping the latest snapshot
// mid-request; the handler must have captured snapA exactly once.
type swappingProvider struct {
	mu    sync.Mutex
	calls int
	snapA *collectors.Snapshot
	snapB *collectors.Snapshot
}

func (p *swappingProvider) Latest() *collectors.Snapshot {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.calls++
	if p.calls == 1 {
		return p.snapA
	}
	return p.snapB
}

func (p *swappingProvider) Calls() int {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.calls
}

// TestCoherentSnapshotUnderSwap proves that data, observedAt and nextCursor are
// all derived from the SAME snapshot even if the collector swaps the latest
// snapshot between the handler's stages.
func TestCoherentSnapshotUnderSwap(t *testing.T) {
	t1 := time.Date(2026, 10, 21, 0, 0, 0, 0, time.UTC)
	t2 := t1.Add(2 * time.Hour)

	snapA := &collectors.Snapshot{
		CollectedAt: t1,
		Nodes: []model.Node{
			{Name: "node-A1", UID: "a1", Ready: "True", Health: "healthy", Conditions: []model.Condition{}},
			{Name: "node-A2", UID: "a2", Ready: "True", Health: "healthy", Conditions: []model.Condition{}},
			{Name: "node-A3", UID: "a3", Ready: "True", Health: "healthy", Conditions: []model.Condition{}},
		},
	}
	snapB := &collectors.Snapshot{
		CollectedAt: t2,
		Nodes:       []model.Node{{Name: "node-B1", UID: "b1", Ready: "True", Health: "healthy", Conditions: []model.Condition{}}},
	}

	prov := &swappingProvider{snapA: snapA, snapB: snapB}
	sum := sha256.Sum256([]byte("test-password"))
	verifier, _ := auth.NewVerifier("portal-operator", hex.EncodeToString(sum[:]))
	s := &Server{
		collector: prov,
		store:     mockStore{},
		verifier:  verifier,
		cfg:       &config.Config{SourceRevision: strings.Repeat("a", 40)},
		rate:      newTokenBucket(1000),
		sem:       make(chan struct{}, 20),
	}

	req := httptest.NewRequest(http.MethodGet, "/api/v1/nodes?limit=1", nil)
	req.SetBasicAuth("portal-operator", "test-password")
	rr := httptest.NewRecorder()
	s.Handler().ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Fatalf("status: %d", rr.Code)
	}

	var body map[string]any
	if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
		t.Fatalf("json: %v", err)
	}

	// data must be from snapA (first node, not snapB's node).
	items := body["data"].(map[string]any)["items"].([]any)
	if len(items) != 1 {
		t.Fatalf("expected 1 item, got %d", len(items))
	}
	gotName := items[0].(map[string]any)["name"].(string)
	if gotName != "node-A1" {
		t.Fatalf("expected data from snapA (node-A1), got %s", gotName)
	}

	// observedAt must be snapA's CollectedAt (t1), not t2.
	observedAt, _ := body["observedAt"].(string)
	if observedAt != t1.UTC().Format(time.RFC3339) {
		t.Fatalf("observedAt must be from snapA (%s), got %s", t1.Format(time.RFC3339), observedAt)
	}

	// nextCursor must be bound to snapA's snapshot id (t1 nano), not t2.
	nc, _ := body["nextCursor"].(string)
	if nc == "" {
		t.Fatal("expected nextCursor")
	}
	cs, err := decodeCursor(nc)
	if err != nil {
		t.Fatalf("decode cursor: %v", err)
	}
	wantID := snapshotIDFor(snapA)
	if cs.snapshotID != wantID {
		t.Fatalf("nextCursor bound to wrong snapshot: got %s want %s", cs.snapshotID, wantID)
	}

	// The provider may be called multiple times; the key property is that the
	// response is coherent. Record how many Latest() calls happened for the log.
	if prov.Calls() == 0 {
		t.Fatal("provider was never called")
	}
}
