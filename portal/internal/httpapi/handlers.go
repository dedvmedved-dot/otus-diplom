package httpapi

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

func newRequestID() string {
	b := make([]byte, 12)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// snapshot returns the latest snapshot or a synthetic empty one.
func (s *Server) snapshot() *collectors.Snapshot {
	snap := s.collector.Latest()
	if snap == nil {
		return &collectors.Snapshot{CollectedAt: time.Time{}, OverallHealth: "unknown"}
	}
	return snap
}

// envelope builds the common response wrapper from a snapshot.
func (s *Server) envelope(snap *collectors.Snapshot) model.Envelope {
	var obs *string
	freshness := "unknown"
	if !snap.CollectedAt.IsZero() {
		o := snap.CollectedAt.UTC().Format(time.RFC3339)
		obs = &o
		age := time.Since(snap.CollectedAt)
		switch {
		case age <= 90*time.Second:
			freshness = "fresh"
		case age <= 5*time.Minute:
			freshness = "stale"
		default:
			freshness = "unknown"
		}
	}
	return model.Envelope{
		RequestID:   newRequestID(),
		GeneratedAt: time.Now().UTC().Format(time.RFC3339),
		ObservedAt:  obs,
		Freshness:   freshness,
		Partial:     snap.Partial,
		Sources:     snap.Sources,
		Warnings:    snap.Warnings,
	}
}

// query helpers -------------------------------------------------------------

// parseListQuery parses limit/cursor/namespace; returns limit, offset, namespace.
func parseListQuery(r *http.Request) (limit int, offset int, namespace string, err error) {
	limit = 50
	if v := r.URL.Query().Get("limit"); v != "" {
		n, e := strconv.Atoi(v)
		if e != nil || n < 1 || n > 200 {
			return 0, 0, "", errBadQuery("limit")
		}
		limit = n
	}
	if v := r.URL.Query().Get("cursor"); v != "" {
		if len(v) > 512 {
			return 0, 0, "", errBadQuery("cursor")
		}
		raw, e := base64.RawURLEncoding.DecodeString(v)
		if e != nil {
			return 0, 0, "", errBadQuery("cursor")
		}
		off, e := strconv.Atoi(string(raw))
		if e != nil || off < 0 {
			return 0, 0, "", errBadQuery("cursor")
		}
		offset = off
	}
	namespace = r.URL.Query().Get("namespace")
	if namespace != "" {
		if len(namespace) > 63 || !dns1123(namespace) {
			return 0, 0, "", errBadQuery("namespace")
		}
	}
	return limit, offset, namespace, nil
}

type queryError struct{ field string }

func (q queryError) Error() string { return "invalid query: " + q.field }

func errBadQuery(field string) error { return queryError{field: field} }

func dns1123(s string) bool {
	if len(s) == 0 {
		return false
	}
	for i := 0; i < len(s); i++ {
		c := s[i]
		if (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' {
			continue
		}
		return false
	}
	return s[0] != '-' && s[len(s)-1] != '-'
}

// paginate slices an already-sorted slice and returns the page + next cursor.
func paginate[T any](items []T, limit, offset int) ([]T, *string) {
	if offset >= len(items) {
		return []T{}, nil
	}
	end := offset + limit
	if end > len(items) {
		end = len(items)
	}
	page := items[offset:end]
	var next *string
	if end < len(items) {
		c := base64.RawURLEncoding.EncodeToString([]byte(strconv.Itoa(end)))
		next = &c
	}
	return page, next
}

// handlers ------------------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	snap := s.snapshot()
	dbState := "connected"
	ver, _, err := s.store.CurrentMigrationVersion(r.Context())
	if err != nil || ver == 0 {
		dbState = "disconnected"
	}
	data := model.HealthInfo{
		Process:        "running",
		DBConnectivity: dbState,
		SchemaVersion:  strconv.FormatInt(ver, 10),
		Collector:      "running",
		Build:          s.cfg.SourceRevision,
	}
	env := s.envelope(snap)
	env.Data = data
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleSummary(w http.ResponseWriter, r *http.Request) {
	snap := s.snapshot()
	counts := map[string]int{
		"nodes":     len(snap.Nodes),
		"workloads": len(snap.Workloads),
		"pods":      len(snap.Pods),
		"services":  len(snap.Services),
		"storage":   len(snap.Storage),
		"backups":   len(snap.Backups),
		"metrics":   len(snap.Metrics),
	}
	data := model.SummaryInfo{
		OverallHealth: snap.OverallHealth,
		Counts:        counts,
		Alerts:        snap.Warnings,
		PolicyGaps:    policyGaps(),
	}
	if !snap.CollectedAt.IsZero() {
		t := snap.CollectedAt
		data.ObservedAt = &t
	}
	env := s.envelope(snap)
	env.Data = data
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleNodes(w http.ResponseWriter, r *http.Request) {
	limit, offset, _, err := parseListQuery(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "INVALID_QUERY", err.Error())
		return
	}
	snap := s.snapshot()
	page, next := paginate(snap.Nodes, limit, offset)
	env := s.envelope(snap)
	env.Data = page
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleWorkloads(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := parseListQuery(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "INVALID_QUERY", err.Error())
		return
	}
	snap := s.snapshot()
	items := filterWorkloads(snap.Workloads, ns)
	page, next := paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = page
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handlePods(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := parseListQuery(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "INVALID_QUERY", err.Error())
		return
	}
	snap := s.snapshot()
	items := filterPods(snap.Pods, ns)
	page, next := paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = page
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleServices(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := parseListQuery(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "INVALID_QUERY", err.Error())
		return
	}
	snap := s.snapshot()
	items := filterServices(snap.Services, ns)
	page, next := paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = page
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleStorage(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := parseListQuery(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "INVALID_QUERY", err.Error())
		return
	}
	snap := s.snapshot()
	items := filterStorage(snap.Storage, ns)
	page, next := paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = page
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleBackups(w http.ResponseWriter, r *http.Request) {
	limit, offset, _, err := parseListQuery(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "INVALID_QUERY", err.Error())
		return
	}
	snap := s.snapshot()
	page, next := paginate(snap.Backups, limit, offset)
	env := s.envelope(snap)
	env.Data = page
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleDatabase(w http.ResponseWriter, r *http.Request) {
	snap := s.snapshot()
	env := s.envelope(snap)
	if snap.Database == nil {
		env.Data = map[string]any{"name": "portal-db", "ready": 0, "desired": 0}
	} else {
		env.Data = snap.Database
	}
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleMetrics(w http.ResponseWriter, r *http.Request) {
	limit, offset, _, err := parseListQuery(r)
	if err != nil {
		writeError(w, http.StatusBadRequest, "INVALID_QUERY", err.Error())
		return
	}
	snap := s.snapshot()
	page, next := paginate(snap.Metrics, limit, offset)
	env := s.envelope(snap)
	env.Data = page
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleEvents(w http.ResponseWriter, r *http.Request) {
	limit := 50
	if v := r.URL.Query().Get("limit"); v != "" {
		n, e := strconv.Atoi(v)
		if e != nil || n < 1 || n > 200 {
			writeError(w, http.StatusBadRequest, "INVALID_QUERY", "limit")
			return
		}
		limit = n
	}
	var since *time.Time
	if v := r.URL.Query().Get("since"); v != "" {
		t, e := time.Parse(time.RFC3339, v)
		if e != nil {
			writeError(w, http.StatusBadRequest, "INVALID_QUERY", "since")
			return
		}
		since = &t
	}
	severity := r.URL.Query().Get("severity")
	if severity != "" && severity != "normal" && severity != "warning" && severity != "critical" {
		writeError(w, http.StatusBadRequest, "INVALID_QUERY", "severity")
		return
	}
	rows, err := s.store.ListEvents(r.Context(), since, severity, limit)
	if err != nil {
		writeError(w, http.StatusServiceUnavailable, "EVENTS_UNAVAILABLE", "events store unavailable")
		return
	}
	events := make([]model.EventInfo, 0, len(rows))
	for _, row := range rows {
		var st *string
		if row.SourceTime != nil {
			v := row.SourceTime.UTC().Format(time.RFC3339)
			st = &v
		}
		events = append(events, model.EventInfo{
			IngestedAt:  row.IngestedAt.UTC().Format(time.RFC3339),
			SourceTime:  st,
			Source:      row.Source,
			Severity:    row.Severity,
			ObjectKind:  row.ObjectKind,
			ObjectNS:    row.ObjectNS,
			ObjectName:  row.ObjectName,
			ReasonCode:  row.ReasonCode,
			Occurrences: row.Occurrences,
			Message:     row.Message,
		})
	}
	env := s.envelope(s.snapshot())
	env.Data = events
	writeJSON(w, http.StatusOK, env)
}

// namespace filters ---------------------------------------------------------

func filterWorkloads(items []model.WorkloadInfo, ns string) []model.WorkloadInfo {
	if ns == "" {
		return items
	}
	out := make([]model.WorkloadInfo, 0, len(items))
	for _, it := range items {
		if it.Namespace == ns {
			out = append(out, it)
		}
	}
	return out
}

func filterPods(items []model.PodInfo, ns string) []model.PodInfo {
	if ns == "" {
		return items
	}
	out := make([]model.PodInfo, 0, len(items))
	for _, it := range items {
		if it.Namespace == ns {
			out = append(out, it)
		}
	}
	return out
}

func filterServices(items []model.ServiceInfo, ns string) []model.ServiceInfo {
	if ns == "" {
		return items
	}
	out := make([]model.ServiceInfo, 0, len(items))
	for _, it := range items {
		if it.Namespace == ns {
			out = append(out, it)
		}
	}
	return out
}

func filterStorage(items []model.StorageInfo, ns string) []model.StorageInfo {
	if ns == "" {
		return items
	}
	out := make([]model.StorageInfo, 0, len(items))
	for _, it := range items {
		if it.Namespace == ns || it.Namespace == "" {
			out = append(out, it)
		}
	}
	return out
}

// policyGaps returns the carried-forward backup policy gaps (visible, not fixed).
func policyGaps() []string {
	return []string{
		"TR_PG_WAL_14D = IMPLEMENTED_POLICY",
		"TR_PG_FULL_8_COPIES = POLICY_CAPABLE_NOT_TIME_AGED",
		"TR_PG_INCREMENTAL_DIFFERENTIAL_14 = NOT_IMPLEMENTED_IN_SELECTED_PLUGIN_PATH",
		"TR_MONTHLY_CONTROL_12 = DEFERRED_TO_P8G_P9_POLICY_CLOSURE",
	}
}

var _ = strings.TrimSpace
