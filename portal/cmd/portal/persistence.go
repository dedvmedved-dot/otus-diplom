package main

import (
	"context"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/store"
	"time"
)

type persistenceWriter interface {
	InsertBatch(context.Context, string, time.Time, string, string, bool, []byte) error
	UpsertEvent(context.Context, store.TimelineEvent) error
	Prune(context.Context) error
}
type snapshotReader interface{ Latest() *collectors.Snapshot }
type pendingBatch struct {
	id               string
	at               time.Time
	revision, health string
	partial          bool
	summary          []byte
}
type persister struct {
	ps           *collectors.PersistenceState
	batches      []pendingBatch
	events       []model.TimelineEvent
	lastSnapshot string
	states       map[string]string
}

const maxPendingEvents = 500
const maxPendingBatches = 16

func newPersister(ps *collectors.PersistenceState) *persister {
	ps.LagSeconds.Store(-1)
	return &persister{ps: ps, states: map[string]string{}}
}
func (p *persister) enqueue(e model.TimelineEvent) {
	for i := range p.events {
		if p.events[i].ID == e.ID {
			p.events[i] = e
			return
		}
	}
	if e.Source == "portal-status" {
		count := 0
		first := -1
		for i, item := range p.events {
			if item.Source == "portal-status" {
				count++
				if first < 0 {
					first = i
				}
			}
		}
		if count >= collectors.MaxTransitions {
			p.events = append(p.events[:first], p.events[first+1:]...)
			p.ps.DataLoss.Store(true)
		}
	}
	if len(p.events) >= maxPendingEvents {
		p.events = p.events[1:]
		p.ps.DataLoss.Store(true)
	}
	p.events = append(p.events, e)
}
func (p *persister) transition(kind, state string) {
	if p.states[kind] == state {
		return
	}
	p.states[kind] = state
	now := time.Now().UTC()
	stamp := now.Format(time.RFC3339Nano)
	severity := "normal"
	if state == "failed" || state == "warning" || state == "unknown" {
		severity = "warning"
	}
	if state == "critical" {
		severity = "critical"
	}
	p.enqueue(model.TimelineEvent{ID: "portal-" + kind + "-" + newUUIDDeterministic(now), Source: "portal-status", SourceTime: &stamp, IngestedAt: stamp, Severity: severity, ReasonCode: "PORTAL_" + kind, OccurrenceCount: 1, Message: kind + "=" + state})
	if kind == "persistence" {
		p.ps.RecordTransition(state)
	}
}
func (p *persister) failed() {
	p.ps.Failed.Store(true)
	p.ps.LagSeconds.Store(-1)
	if last := p.ps.LastSuccessUnix.Load(); last > 0 {
		p.ps.LagSeconds.Store(time.Now().Unix() - last)
	}
	p.transition("persistence", "failed")
}
func (p *persister) once(ctx context.Context, st persistenceWriter, col snapshotReader, cfg *config.Config) {
	ctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()
	defer func() { p.ps.SetFallback(p.events) }()
	snap := col.Latest()
	if snap != nil {
		id := newUUIDDeterministic(snap.CollectedAt)
		if id != p.lastSnapshot {
			p.lastSnapshot = id
			health := snapshotHealth(snap)
			p.transition("platform", health)
			if len(p.batches) >= maxPendingBatches {
				p.batches = p.batches[1:]
				p.ps.DataLoss.Store(true)
			}
			p.batches = append(p.batches, pendingBatch{id, snap.CollectedAt, cfg.SourceRevision, health, snap.Partial, buildSummaryJSON(snap)})
			for _, e := range snap.Events {
				p.enqueue(e)
			}
		}
	}
	if snap == nil && len(p.batches) == 0 && len(p.events) == 0 {
		return
	}
	for len(p.batches) > 0 {
		b := p.batches[0]
		if err := st.InsertBatch(ctx, b.id, b.at, b.revision, b.health, b.partial, b.summary); err != nil {
			p.failed()
			return
		}
		p.batches = p.batches[1:]
	}
	for len(p.events) > 0 {
		e := p.events[0]
		row := store.TimelineEvent{DedupKey: e.ID, Source: e.Source, SourceUID: e.SourceUID, SourceResourceVersion: e.SourceResourceVersion, Severity: e.Severity, ReasonCode: e.ReasonCode, Occurrences: e.OccurrenceCount, Message: e.Message}
		if e.SourceTime != nil {
			if t, err := time.Parse(time.RFC3339Nano, *e.SourceTime); err == nil {
				row.SourceTime = &t
			}
		}
		if e.ObjectKind != nil {
			row.ObjectKind = *e.ObjectKind
		}
		if e.Namespace != nil {
			row.ObjectNamespace = *e.Namespace
		}
		if e.ObjectName != nil {
			row.ObjectName = *e.ObjectName
		}
		if err := st.UpsertEvent(ctx, row); err != nil {
			p.failed()
			return
		}
		p.events = p.events[1:]
	}
	p.ps.LastSuccessUnix.Store(time.Now().Unix())
	p.ps.LagSeconds.Store(0)
	if p.ps.Failed.Swap(false) {
		p.transition("persistence", "recovered")
	} else if p.states["persistence"] == "" {
		p.transition("persistence", "ok")
	}
	// DataLoss is latched for this process lifetime after a bounded queue drop;
	// a later successful write cannot reconstruct a discarded observation.
}
func (p *persister) cleanup(ctx context.Context, st persistenceWriter) {
	if err := st.Prune(ctx); err != nil {
		p.failed()
		p.transition("retention", "failed")
	} else {
		p.transition("retention", "ok")
	}
	p.ps.SetFallback(p.events)
}
