package main

import (
	"testing"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

func TestMarkPersistenceFailureInitialLag(t *testing.T) {
	ps := &collectors.PersistenceState{}
	markPersistenceFailure(ps)
	if ps.LagSeconds.Load() != -1 {
		t.Fatalf("expected initial lag -1 (never succeeded), got %d", ps.LagSeconds.Load())
	}
	if !ps.DataLoss.Load() {
		t.Fatal("expected dataLoss=true")
	}
	tr := ps.Transitions()
	if len(tr) != 1 || tr[0].State != "failed" {
		t.Fatalf("expected one 'failed' transition, got %v", tr)
	}
}

func TestPersistenceRecovery(t *testing.T) {
	ps := &collectors.PersistenceState{}
	markPersistenceFailure(ps)
	// Simulate success: lag 0, last success, clear data loss, record recovered.
	ps.LagSeconds.Store(0)
	ps.LastSuccessUnix.Store(time.Now().Unix())
	if ps.DataLoss.Swap(false) {
		ps.RecordTransition("recovered")
	} else {
		ps.RecordTransition("ok")
	}
	tr := ps.Transitions()
	if len(tr) != 2 || tr[0].State != "failed" || tr[1].State != "recovered" {
		t.Fatalf("expected failed->recovered, got %v", tr)
	}
	if ps.LagSeconds.Load() != 0 {
		t.Fatalf("expected lag 0 after recovery, got %d", ps.LagSeconds.Load())
	}
}

func TestPersistenceElapsedLag(t *testing.T) {
	ps := &collectors.PersistenceState{}
	ps.LastSuccessUnix.Store(time.Now().Add(-10 * time.Second).Unix())
	markPersistenceFailure(ps)
	lag := ps.LagSeconds.Load()
	if lag < 9 || lag > 11 {
		t.Fatalf("expected elapsed lag ~10s, got %d", lag)
	}
}

func TestTransitionQueueOverflow(t *testing.T) {
	ps := &collectors.PersistenceState{}
	for i := 0; i < 100; i++ {
		ps.RecordTransition("failed")
	}
	tr := ps.Transitions()
	if len(tr) != collectors.MaxTransitions {
		t.Fatalf("expected bounded %d, got %d", collectors.MaxTransitions, len(tr))
	}
}

func TestSnapshotHealthStates(t *testing.T) {
	if snapshotHealth(nil) != "unknown" {
		t.Fatal("nil snapshot must be unknown")
	}
	// Not-ready node -> critical.
	snap := &collectors.Snapshot{
		Nodes: []model.Node{{Ready: "False", Health: "unknown"}},
	}
	if h := snapshotHealth(snap); h != "critical" {
		t.Fatalf("expected critical for not-ready node, got %s", h)
	}
	// Partial -> warning.
	snap = &collectors.Snapshot{Nodes: []model.Node{{Ready: "True", Health: "healthy"}}, Partial: true}
	if h := snapshotHealth(snap); h != "warning" {
		t.Fatalf("expected warning for partial, got %s", h)
	}
	// Database critical -> critical.
	snap = &collectors.Snapshot{
		Nodes:    []model.Node{{Ready: "True", Health: "healthy"}},
		Database: &model.Database{Health: "critical"},
	}
	if h := snapshotHealth(snap); h != "critical" {
		t.Fatalf("expected critical for critical DB, got %s", h)
	}
	// All healthy -> healthy.
	snap = &collectors.Snapshot{Nodes: []model.Node{{Ready: "True", Health: "healthy"}}, Database: &model.Database{Health: "healthy"}}
	if h := snapshotHealth(snap); h != "healthy" {
		t.Fatalf("expected healthy, got %s", h)
	}
}
