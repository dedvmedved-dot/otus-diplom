package main

import (
	"context"
	"errors"
	"fmt"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/store"
	"testing"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

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

type testSnapshot struct{ snap *collectors.Snapshot }

func (p *testSnapshot) Latest() *collectors.Snapshot { return p.snap }

type testWriter struct {
	failBatch, failEvent, failPrune bool
	batches                         map[string]bool
	events                          map[string]store.TimelineEvent
}

func (w *testWriter) InsertBatch(_ context.Context, id string, _ time.Time, _, _ string, _ bool, _ []byte) error {
	if w.failBatch {
		return errors.New("synthetic")
	}
	w.batches[id] = true
	return nil
}
func (w *testWriter) UpsertEvent(_ context.Context, e store.TimelineEvent) error {
	if w.failEvent {
		return errors.New("synthetic")
	}
	w.events[e.DedupKey] = e
	return nil
}
func (w *testWriter) Prune(context.Context) error {
	if w.failPrune {
		return errors.New("synthetic")
	}
	return nil
}
func newTestWriter() *testWriter {
	return &testWriter{batches: map[string]bool{}, events: map[string]store.TimelineEvent{}}
}
func TestProductionPersistenceFailureRecovery(t *testing.T) {
	ps := &collectors.PersistenceState{}
	p := newPersister(ps)
	w := newTestWriter()
	w.failEvent = true
	now := time.Now()
	sourceTime := now.UTC().Format(time.RFC3339)
	provider := &testSnapshot{&collectors.Snapshot{CollectedAt: now, Nodes: []model.Node{{Ready: "True", Health: "healthy"}}, Events: []model.TimelineEvent{{ID: "event-uid", Source: "kubernetes", SourceUID: "uid", SourceResourceVersion: "1", SourceTime: &sourceTime, Severity: "normal", ReasonCode: "Started", Message: "fixture", OccurrenceCount: 1}}}}
	cfg := &config.Config{SourceRevision: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
	p.once(context.Background(), w, provider, cfg)
	if ps.LastSuccessUnix.Load() != 0 || ps.LagSeconds.Load() != -1 || !ps.Failed.Load() {
		t.Fatal("initial failure is not truthful")
	}
	if len(ps.Fallback()) < 2 {
		t.Fatal("failed events and transition must survive in bounded fallback")
	}
	p.once(context.Background(), w, provider, cfg)
	if len(ps.Transitions()) != 1 {
		t.Fatal("unchanged failure must not create another transition")
	}
	w.failEvent = false
	p.once(context.Background(), w, provider, cfg)
	p.once(context.Background(), w, provider, cfg)
	if ps.Failed.Load() || ps.LastSuccessUnix.Load() == 0 || ps.DataLoss.Load() {
		t.Fatal("retained events should recover without claimed loss")
	}
	if len(w.batches) != 1 || w.events["event-uid"].SourceUID != "uid" || w.events["event-uid"].Occurrences != 1 {
		t.Fatal("batch/event identity lost")
	}
	found := false
	for _, e := range w.events {
		if e.Message == "persistence=recovered" {
			found = true
		}
	}
	if !found {
		t.Fatal("recovery was not flushed through production writer")
	}
	if len(ps.Fallback()) != 0 {
		t.Fatal("acknowledged queue must drain")
	}
	w.failPrune = true
	p.cleanup(context.Background(), w)
	if !ps.Failed.Load() {
		t.Fatal("cleanup failure hidden")
	}
	w.failPrune = false
	p.cleanup(context.Background(), w)
	p.once(context.Background(), w, provider, cfg)
	p.once(context.Background(), w, provider, cfg)
	if ps.Failed.Load() {
		t.Fatal("cleanup recovery hidden")
	}
}
func TestProductionQueueOverflowLatchedLoss(t *testing.T) {
	ps := &collectors.PersistenceState{}
	p := newPersister(ps)
	w := newTestWriter()
	w.failBatch = true
	cfg := &config.Config{SourceRevision: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
	provider := &testSnapshot{}
	for i := 0; i < 80; i++ {
		provider.snap = &collectors.Snapshot{CollectedAt: time.Now().Add(time.Duration(i) * time.Second), Partial: i%2 == 0}
		provider.snap.Events = []model.TimelineEvent{{ID: fmt.Sprintf("event-%d", i), Source: "kubernetes", Severity: "normal", ReasonCode: "Test", Message: "fixture", OccurrenceCount: 1}}
		p.once(context.Background(), w, provider, cfg)
	}
	if !ps.DataLoss.Load() || len(p.batches) > maxPendingBatches || len(p.events) > maxPendingEvents {
		t.Fatal("overflow is unbounded or hidden")
	}
	statuses := 0
	for _, e := range p.events {
		if e.Source == "portal-status" {
			statuses++
		}
	}
	if statuses > collectors.MaxTransitions {
		t.Fatal("status queue exceeded cap")
	}
	w.failBatch = false
	p.once(context.Background(), w, provider, cfg)
	p.once(context.Background(), w, provider, cfg)
	if !ps.DataLoss.Load() {
		t.Fatal("successful write must not erase dropped history")
	}
}
