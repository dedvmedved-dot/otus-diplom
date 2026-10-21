package httpapi

import (
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/store"
	"time"
)

// Bounded process-local views, scoped to the collector snapshot and all filters.
// Eviction/restart/90s expiry returns CURSOR_EXPIRED, never a different result set.
type eventView struct {
	snapshot, namespace, since, severity, backend string
	events                                        []model.TimelineEvent
	created                                       time.Time
	partial                                       bool
}

func (s *Server) saveEventView(v eventView) string {
	s.eventMu.Lock()
	defer s.eventMu.Unlock()
	if s.eventViews == nil {
		s.eventViews = map[string]eventView{}
	}
	for id, old := range s.eventViews {
		if time.Since(old.created) > 90*time.Second {
			delete(s.eventViews, id)
		}
	}
	if len(s.eventViews) >= 32 {
		oldest := ""
		var when time.Time
		for id, old := range s.eventViews {
			if oldest == "" || old.created.Before(when) {
				oldest = id
				when = old.created
			}
		}
		delete(s.eventViews, oldest)
	}
	id := newRequestID()
	s.eventViews[id] = v
	return id
}
func (s *Server) readEventView(id, snapshot, namespace, since, severity, backend string) (eventView, bool) {
	s.eventMu.Lock()
	defer s.eventMu.Unlock()
	v, ok := s.eventViews[id]
	if !ok || time.Since(v.created) > 90*time.Second || v.snapshot != snapshot || v.namespace != namespace || v.since != since || v.severity != severity || v.backend != backend {
		return eventView{}, false
	}
	return v, true
}
func eventRows(rows []store.EventRow) []model.TimelineEvent {
	events := make([]model.TimelineEvent, 0, len(rows))
	for _, row := range rows {
		var sourceTime *string
		if row.SourceTime != nil {
			v := row.SourceTime.UTC().Format(time.RFC3339Nano)
			sourceTime = &v
		}
		events = append(events, model.TimelineEvent{ID: row.ID, Source: row.Source, SourceTime: sourceTime, IngestedAt: row.IngestedAt.UTC().Format(time.RFC3339Nano), Severity: row.Severity, ObjectKind: row.ObjectKind, Namespace: row.ObjectNS, ObjectName: row.ObjectName, ReasonCode: row.ReasonCode, OccurrenceCount: row.Occurrences, Message: row.Message})
	}
	return events
}
