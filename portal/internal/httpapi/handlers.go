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

// snapshot returns the latest snapshot or nil.
func (s *Server) snapshot() *collectors.Snapshot {
	if s.collector == nil {
		return nil
	}
	return s.collector.Latest()
}

// envelope builds the common response wrapper from a snapshot.
func (s *Server) envelope(snap *collectors.Snapshot) model.Envelope {
	var obs *string
	freshness := "unavailable"
	var sources []model.SourceStatus
	var warnings []model.Warning
	partial := false
	if snap != nil {
		sources = snap.Sources
		warnings = snap.Warnings
		if sources == nil {
			sources = []model.SourceStatus{}
		}
		if warnings == nil {
			warnings = []model.Warning{}
		}
		partial = snap.Partial
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
				freshness = "unavailable"
			}
		}
	}
	return model.Envelope{
		RequestID:   newRequestID(),
		GeneratedAt: time.Now().UTC().Format(time.RFC3339),
		ObservedAt:  obs,
		Freshness:   freshness,
		Partial:     partial,
		Sources:     sources,
		Warnings:    warnings,
	}
}

// snapshotID returns a stable id for the current snapshot (for cursor binding).
func (s *Server) snapshotID() string {
	snap := s.snapshot()
	if snap == nil || snap.CollectedAt.IsZero() {
		return ""
	}
	return strconv.FormatInt(snap.CollectedAt.UnixNano(), 10)
}

// cursorState decodes a snapshot-bound cursor.
type cursorState struct {
	snapshotID string
	offset     int
}

func encodeCursor(snapID string, offset int) string {
	return base64.RawURLEncoding.EncodeToString([]byte(snapID + ":" + strconv.Itoa(offset)))
}

func decodeCursor(cursor string) (cursorState, error) {
	raw, err := base64.RawURLEncoding.DecodeString(cursor)
	if err != nil {
		return cursorState{}, errBadQuery("cursor")
	}
	parts := strings.SplitN(string(raw), ":", 2)
	if len(parts) != 2 {
		return cursorState{}, errBadQuery("cursor")
	}
	off, err := strconv.Atoi(parts[1])
	if err != nil || off < 0 {
		return cursorState{}, errBadQuery("cursor")
	}
	return cursorState{snapshotID: parts[0], offset: off}, nil
}

type queryError struct{ field string }

func (q queryError) Error() string { return "invalid query: " + q.field }

func errBadQuery(field string) error { return queryError{field: field} }

func dns1123(s string) bool {
	if len(s) == 0 || len(s) > 63 {
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

// parseListQuery validates allowed keys and returns limit, cursor offset, namespace.
func (s *Server) parseListQuery(r *http.Request, allowed []string) (limit int, offset int, namespace string, err error) {
	limit = 50
	offset = 0
	namespace = ""
	allowedSet := map[string]bool{}
	for _, k := range allowed {
		allowedSet[k] = true
	}
	for k := range r.URL.Query() {
		if !allowedSet[k] {
			return 0, 0, "", errBadQuery(k)
		}
	}
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
		cs, e := decodeCursor(v)
		if e != nil {
			return 0, 0, "", e
		}
		if cs.snapshotID != s.snapshotID() {
			return 0, 0, "", errCursorExpired{}
		}
		offset = cs.offset
	}
	if v := r.URL.Query().Get("namespace"); v != "" {
		if !dns1123(v) {
			return 0, 0, "", errBadQuery("namespace")
		}
		namespace = v
	}
	return limit, offset, namespace, nil
}

type errCursorExpired struct{}

func (errCursorExpired) Error() string { return "cursor expired" }

// paginate slices a sorted slice and returns the page + next cursor.
func (s *Server) paginate[T any](items []T, limit, offset int) ([]T, *string) {
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
		c := encodeCursor(s.snapshotID(), end)
		next = &c
	}
	return page, next
}

// ---- handlers ------------------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	snap := s.snapshot()
	dbState := "unknown"
	var schemaVersion *int64
	ver, _, err := s.store.CurrentMigrationVersion(r.Context())
	if err == nil && ver >= 1 {
		schemaVersion = &ver
		dbState = "connected"
	} else if err != nil {
		dbState = "disconnected"
	}

	collectorState := "starting"
	if snap != nil {
		collectorState = "running"
		if snap.Partial {
			collectorState = "degraded"
		}
	}

	status := "unknown"
	switch {
	case dbState == "connected" && collectorState == "running":
		status = "healthy"
	case dbState == "disconnected":
		status = "warning"
	case collectorState == "degraded":
		status = "warning"
	}

	var lag *float64
	if s.ps != nil {
		v := float64(s.ps.LagSeconds.Load())
		lag = &v
	}
	dataLoss := false
	if s.ps != nil {
		dataLoss = s.ps.DataLoss.Load()
	}

	data := model.Health{
		Status:                status,
		BuildRevision:         s.cfg.SourceRevision,
		ApplicationDb:         dbState,
		SchemaVersion:         schemaVersion,
		CollectorState:        collectorState,
		PersistenceLagSeconds: lag,
		DataLoss:              dataLoss,
	}
	env := s.envelope(snap)
	env.Data = data
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleSummary(w http.ResponseWriter, r *http.Request) {
	if err := requireNoQuery(r); err != nil {
		writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
		return
	}
	snap := s.snapshot()
	counts := model.Counts{NodesExpected: 3}
	if snap != nil {
		var nodesObserved, nodesReady, podsObserved, podsReady, pvcObserved, pvcBound int64
		for _, n := range snap.Nodes {
			nodesObserved++
			if n.Ready == "True" {
				nodesReady++
			}
		}
		for _, p := range snap.Pods {
			podsObserved++
			if p.Health == "healthy" {
				podsReady++
			}
		}
		if snap.Storage != nil {
			for _, it := range snap.Storage.Items {
				if it.Kind == "PersistentVolumeClaim" {
					pvcObserved++
					if it.Phase != nil && *it.Phase == "Bound" {
						pvcBound++
					}
				}
			}
		}
		counts.NodesObserved = &nodesObserved
		counts.NodesReady = &nodesReady
		counts.PodsObserved = &podsObserved
		counts.PodsReady = &podsReady
		counts.PvcObserved = &pvcObserved
		counts.PvcBound = &pvcBound
		if snap.Database != nil {
			if snap.Database.DesiredInstances != nil {
				d := int64(*snap.Database.DesiredInstances)
				counts.PostgresDesired = &d
			}
			if snap.Database.ReadyInstances != nil {
				r := int64(*snap.Database.ReadyInstances)
				counts.PostgresReady = &r
			}
		}
	}

	overall := aggregateSummaryHealth(counts, snap)
	subsystems := buildSubsystems(snap)
	data := model.Summary{
		Overall:    overall,
		Counts:     counts,
		Subsystems: subsystems,
		Alerts:     warningsOrEmpty(snap),
		Coverage:   "mvp-read-only-kubernetes-view",
	}
	env := s.envelope(snap)
	env.Data = data
	writeJSON(w, http.StatusOK, env)
}

func requireNoQuery(r *http.Request) error {
	if len(r.URL.Query()) > 0 {
		for k := range r.URL.Query() {
			return errBadQuery(k)
		}
	}
	return nil
}

func warningsOrEmpty(snap *collectors.Snapshot) []model.Warning {
	if snap == nil {
		return []model.Warning{}
	}
	if snap.Warnings == nil {
		return []model.Warning{}
	}
	return snap.Warnings
}

func aggregateSummaryHealth(c model.Counts, snap *collectors.Snapshot) string {
	if snap == nil {
		return "unknown"
	}
	hasCritical, hasWarning, hasUnknown := false, false, false
	// nodes
	if c.NodesReady != nil && c.NodesObserved != nil {
		if *c.NodesReady < *c.NodesObserved {
			hasCritical = true
		}
	}
	// postgres
	if c.PostgresDesired != nil && c.PostgresReady != nil {
		if *c.PostgresReady < *c.PostgresDesired {
			hasWarning = true
		}
	}
	// subsystems
	for _, sub := range buildSubsystems(snap) {
		switch sub.Health {
		case "critical":
			hasCritical = true
		case "warning":
			hasWarning = true
		case "unknown":
			hasUnknown = true
		}
	}
	if hasCritical {
		return "critical"
	}
	if hasWarning {
		return "warning"
	}
	if hasUnknown {
		return "unknown"
	}
	return "healthy"
}

func buildSubsystems(snap *collectors.Snapshot) []model.Subsystem {
	if snap == nil {
		return []model.Subsystem{}
	}
	subs := []model.Subsystem{}
	var ts *string
	if !snap.CollectedAt.IsZero() {
		v := snap.CollectedAt.UTC().Format(time.RFC3339)
		ts = &v
	}
	subs = append(subs, model.Subsystem{ID: "nodes", Health: subsystemNodesHealth(snap), Scope: "kubernetes_nodes", ObservedAt: ts, Message: "nodes ready/observed"})
	subs = append(subs, model.Subsystem{ID: "workloads", Health: subsystemWorkloadsHealth(snap), Scope: "kubernetes_workloads", ObservedAt: ts, Message: "deployments/sts/ds/rs/job/cronjob"})
	subs = append(subs, model.Subsystem{ID: "storage", Health: subsystemStorageHealth(snap), Scope: "kubernetes_objects", ObservedAt: ts, Message: "pvc/pv/sc/snapshot; DRBD not observed"})
	subs = append(subs, model.Subsystem{ID: "velero", Health: subsystemVeleroHealth(snap), Scope: "velero_bsl_backup_restore", ObservedAt: ts, Message: "velero backup domain"})
	subs = append(subs, model.Subsystem{ID: "postgresql", Health: subsystemDBHealth(snap), Scope: "cnpg_cluster", ObservedAt: ts, Message: "postgresql cluster"})
	subs = append(subs, model.Subsystem{ID: "postgresql-backup", Health: subsystemPGBackupHealth(snap), Scope: "cnpg_barman", ObservedAt: ts, Message: "postgresql backup/WAL"})
	subs = append(subs, model.Subsystem{ID: "application-db", Health: "unknown", Scope: "portal_app_db", ObservedAt: ts, Message: "portal application schema"})
	subs = append(subs, model.Subsystem{ID: "metrics", Health: subsystemMetricsHealth(snap), Scope: "metrics_server", ObservedAt: ts, Message: "metrics server samples"})
	return subs
}

func nowPtrString() *string { t := time.Now().UTC().Format(time.RFC3339); return &t }

func subsystemNodesHealth(snap *collectors.Snapshot) string {
	if len(snap.Nodes) == 0 {
		return "unknown"
	}
	for _, n := range snap.Nodes {
		if n.Ready != "True" {
			return "critical"
		}
	}
	return "healthy"
}

func subsystemWorkloadsHealth(snap *collectors.Snapshot) string {
	hs := []string{}
	for _, w := range snap.Workloads {
		hs = append(hs, w.Health)
	}
	return aggregate(hs)
}

func subsystemStorageHealth(snap *collectors.Snapshot) string {
	if snap.Storage == nil {
		return "unknown"
	}
	hs := []string{}
	for _, it := range snap.Storage.Items {
		hs = append(hs, it.Health)
	}
	return aggregate(hs)
}

func subsystemVeleroHealth(snap *collectors.Snapshot) string {
	if snap.Backups == nil {
		return "unknown"
	}
	return snap.Backups.Velero.Health
}

func subsystemDBHealth(snap *collectors.Snapshot) string {
	if snap.Database == nil {
		return "unknown"
	}
	return snap.Database.Health
}

func subsystemPGBackupHealth(snap *collectors.Snapshot) string {
	if snap.Backups == nil {
		return "unknown"
	}
	return snap.Backups.Postgresql.Health
}

func subsystemMetricsHealth(snap *collectors.Snapshot) string {
	if len(snap.Metrics) == 0 {
		return "unknown"
	}
	return "healthy"
}

func aggregate(hs []string) string {
	hasCritical, hasWarning, hasUnknown, hasAny := false, false, false, false
	for _, h := range hs {
		if h == "" {
			continue
		}
		hasAny = true
		switch h {
		case "critical":
			hasCritical = true
		case "warning":
			hasWarning = true
		case "unknown":
			hasUnknown = true
		}
	}
	if !hasAny {
		return "unknown"
	}
	if hasCritical {
		return "critical"
	}
	if hasWarning {
		return "warning"
	}
	if hasUnknown {
		return "unknown"
	}
	return "healthy"
}

func (s *Server) handleNodes(w http.ResponseWriter, r *http.Request) {
	limit, offset, _, err := s.parseListQuery(r, []string{"limit", "cursor"})
	if err != nil {
		writeListError(w, err)
		return
	}
	snap := s.snapshot()
	var items []model.Node
	if snap != nil {
		items = snap.Nodes
	}
	page, next := s.paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = model.Nodes{Items: page}
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleWorkloads(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := s.parseListQuery(r, []string{"limit", "cursor", "namespace"})
	if err != nil {
		writeListError(w, err)
		return
	}
	snap := s.snapshot()
	var items []model.Workload
	if snap != nil {
		items = snap.Workloads
	}
	items = filterWorkloads(items, ns)
	page, next := s.paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = model.Workloads{Items: page}
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handlePods(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := s.parseListQuery(r, []string{"limit", "cursor", "namespace"})
	if err != nil {
		writeListError(w, err)
		return
	}
	snap := s.snapshot()
	var items []model.Pod
	if snap != nil {
		items = snap.Pods
	}
	items = filterPods(items, ns)
	page, next := s.paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = model.Pods{Items: page}
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleServices(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := s.parseListQuery(r, []string{"limit", "cursor", "namespace"})
	if err != nil {
		writeListError(w, err)
		return
	}
	snap := s.snapshot()
	var items []model.Service
	if snap != nil {
		items = snap.Services
	}
	items = filterServices(items, ns)
	page, next := s.paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = model.Services{Items: page}
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleStorage(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := s.parseListQuery(r, []string{"limit", "cursor", "namespace"})
	if err != nil {
		writeListError(w, err)
		return
	}
	snap := s.snapshot()
	var data model.Storage
	if snap != nil && snap.Storage != nil {
		data = *snap.Storage
	} else {
		data = model.Storage{Scope: "kubernetes_objects", DrbdDirectHealth: "not_observed", Items: []model.StorageItem{}}
	}
	items := filterStorage(data.Items, ns)
	page, next := s.paginate(items, limit, offset)
	data.Items = page
	env := s.envelope(snap)
	env.Data = data
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleBackups(w http.ResponseWriter, r *http.Request) {
	if err := requireNoQuery(r); err != nil {
		writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
		return
	}
	snap := s.snapshot()
	var data model.Backups
	if snap != nil && snap.Backups != nil {
		data = *snap.Backups
	} else {
		data = model.Backups{
			Velero:     model.VeleroBackups{Locations: []model.BackupStorageLocation{}, Backups: []model.BackupRecord{}, Restores: []model.BackupRecord{}, Health: "unknown"},
			Postgresql: model.PostgresBackups{Cluster: "portal-db", ObjectStore: "portal-db-backup", ExpectedSchedule: "0 0 2 * * *", ExpectedTarget: "prefer-standby", Backups: []model.BackupRecord{}, Wal: model.Wal{ExpectedArchiveTimeoutSeconds: 300}, Barman: model.BarmanSample{Scope: "single_exporter_sample"}, Health: "unknown"},
			PolicyGaps: policyGaps(),
		}
	}
	env := s.envelope(snap)
	env.Data = data
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleDatabase(w http.ResponseWriter, r *http.Request) {
	if err := requireNoQuery(r); err != nil {
		writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
		return
	}
	snap := s.snapshot()
	var data model.Database
	if snap != nil && snap.Database != nil {
		data = *snap.Database
	} else {
		data = model.Database{Namespace: "portal", Cluster: "portal-db", Health: "unknown",
			HistoricalQualification: model.HistoricalQualification{Scope: "historical_P8B_evidence", Date: "2026-10-20", LatestRestore: "PASS", Pitr: "PASS", IsLiveRecoveryTest: false}}
	}
	// application DB connectivity reflects the Portal's own store connection.
	appConnected := false
	if err := s.store.Ping(r.Context()); err == nil {
		appConnected = true
	}
	data.ApplicationDbConnected = appConnected
	env := s.envelope(snap)
	env.Data = data
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleMetrics(w http.ResponseWriter, r *http.Request) {
	limit, offset, ns, err := s.parseListQuery(r, []string{"limit", "cursor", "namespace"})
	if err != nil {
		writeListError(w, err)
		return
	}
	snap := s.snapshot()
	var items []model.Metric
	if snap != nil {
		items = snap.Metrics
	}
	items = filterMetrics(items, ns)
	page, next := s.paginate(items, limit, offset)
	env := s.envelope(snap)
	env.Data = model.Metrics{Items: page}
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func (s *Server) handleEvents(w http.ResponseWriter, r *http.Request) {
	limit := 50
	offset := 0
	ns := ""
	var since *time.Time
	severity := ""
	allowed := map[string]bool{"limit": true, "cursor": true, "namespace": true, "since": true, "severity": true}
	for k := range r.URL.Query() {
		if !allowed[k] {
			writeError(w, http.StatusBadRequest, "BAD_REQUEST", "invalid query: "+k)
			return
		}
	}
	if v := r.URL.Query().Get("limit"); v != "" {
		n, e := strconv.Atoi(v)
		if e != nil || n < 1 || n > 200 {
			writeError(w, http.StatusBadRequest, "BAD_REQUEST", "invalid query: limit")
			return
		}
		limit = n
	}
	if v := r.URL.Query().Get("cursor"); v != "" {
		if len(v) > 512 {
			writeError(w, http.StatusBadRequest, "BAD_REQUEST", "invalid query: cursor")
			return
		}
		cs, e := decodeCursor(v)
		if e != nil {
			writeError(w, http.StatusBadRequest, "BAD_REQUEST", "invalid query: cursor")
			return
		}
		if cs.snapshotID != s.snapshotID() {
			writeError(w, http.StatusBadRequest, "CURSOR_EXPIRED", "cursor expired")
			return
		}
		offset = cs.offset
	}
	if v := r.URL.Query().Get("namespace"); v != "" {
		if !dns1123(v) {
			writeError(w, http.StatusBadRequest, "BAD_REQUEST", "invalid query: namespace")
			return
		}
		ns = v
	}
	if v := r.URL.Query().Get("since"); v != "" {
		t, e := time.Parse(time.RFC3339, v)
		if e != nil {
			writeError(w, http.StatusBadRequest, "BAD_REQUEST", "invalid query: since")
			return
		}
		since = &t
	}
	if v := r.URL.Query().Get("severity"); v != "" {
		if v != "normal" && v != "warning" && v != "critical" {
			writeError(w, http.StatusBadRequest, "BAD_REQUEST", "invalid query: severity")
			return
		}
		severity = v
	}

	rows, err := s.store.ListEvents(r.Context(), since, severity, 200)
	if err != nil {
		writeError(w, http.StatusServiceUnavailable, "UNAVAILABLE", "events store unavailable")
		return
	}
	events := make([]model.TimelineEvent, 0, len(rows))
	for _, row := range rows {
		if ns != "" && (row.ObjectNS == "" || row.ObjectNS != ns) {
			continue
		}
		var st *string
		if row.SourceTime != nil {
			v := row.SourceTime.UTC().Format(time.RFC3339)
			st = &v
		}
		events = append(events, model.TimelineEvent{
			ID: row.ID, Source: row.Source, SourceTime: st,
			IngestedAt: row.IngestedAt.UTC().Format(time.RFC3339), Severity: row.Severity,
			ObjectKind: strPtrOrNil(row.ObjectKind), Namespace: strPtrOrNil(row.ObjectNS),
			ObjectName: strPtrOrNil(row.ObjectName), ReasonCode: row.ReasonCode,
			OccurrenceCount: row.Occurrences, Message: row.Message,
		})
	}
	page, next := s.paginate(events, limit, offset)
	data := model.Events{Storage: "postgresql", AuditComplete: false, Items: page}
	env := s.envelope(s.snapshot())
	env.Data = data
	env.NextCursor = next
	writeJSON(w, http.StatusOK, env)
}

func writeListError(w http.ResponseWriter, err error) {
	if _, ok := err.(errCursorExpired); ok {
		writeError(w, http.StatusBadRequest, "CURSOR_EXPIRED", "cursor expired")
		return
	}
	writeError(w, http.StatusBadRequest, "BAD_REQUEST", err.Error())
}

// ---- filters -------------------------------------------------------------------

func filterWorkloads(items []model.Workload, ns string) []model.Workload {
	if ns == "" {
		return items
	}
	out := make([]model.Workload, 0, len(items))
	for _, it := range items {
		if it.Namespace == ns {
			out = append(out, it)
		}
	}
	return out
}

func filterPods(items []model.Pod, ns string) []model.Pod {
	if ns == "" {
		return items
	}
	out := make([]model.Pod, 0, len(items))
	for _, it := range items {
		if it.Namespace == ns {
			out = append(out, it)
		}
	}
	return out
}

func filterServices(items []model.Service, ns string) []model.Service {
	if ns == "" {
		return items
	}
	out := make([]model.Service, 0, len(items))
	for _, it := range items {
		if it.Namespace == ns {
			out = append(out, it)
		}
	}
	return out
}

func filterStorage(items []model.StorageItem, ns string) []model.StorageItem {
	if ns == "" {
		return items
	}
	out := make([]model.StorageItem, 0, len(items))
	for _, it := range items {
		if it.Namespace != nil && *it.Namespace == ns {
			out = append(out, it)
		}
	}
	return out
}

func filterMetrics(items []model.Metric, ns string) []model.Metric {
	if ns == "" {
		return items
	}
	out := make([]model.Metric, 0, len(items))
	for _, it := range items {
		if it.Namespace != nil && *it.Namespace == ns {
			out = append(out, it)
		}
	}
	return out
}

func strPtrOrNil(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}

func policyGaps() []model.PolicyGap {
	return []model.PolicyGap{
		{ID: "TR_PG_WAL_14D", Status: "IMPLEMENTED_POLICY", Explanation: "WAL archiving enabled; retention 14d in ObjectStore."},
		{ID: "TR_PG_FULL_8_COPIES", Status: "POLICY_CAPABLE_NOT_TIME_AGED", Explanation: "Daily schedule capable of >=8 full copies; not yet time-aged."},
		{ID: "TR_PG_INCREMENTAL_DIFFERENTIAL_14", Status: "NOT_IMPLEMENTED_IN_SELECTED_PLUGIN_PATH", Explanation: "Barman Cloud Plugin path does not implement incremental/differential."},
		{ID: "TR_MONTHLY_CONTROL_12", Status: "DEFERRED_TO_P8G_P9_POLICY_CLOSURE", Explanation: "Deferred to P8G/P9 policy closure."},
	}
}
