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

type mockSnapshotProvider struct{ snap *collectors.Snapshot }

func (m mockSnapshotProvider) Latest() *collectors.Snapshot { return m.snap }

type mockStore struct{}

func (mockStore) Ping(ctx context.Context) error { return nil }
func (mockStore) CurrentMigrationVersion(ctx context.Context) (int64, string, error) {
	return 1, strings.Repeat("a", 64), nil
}
func (mockStore) ListEvents(ctx context.Context, since *time.Time, severity, namespace string, limit int, afterID int64) ([]store.EventRow, error) {
	return []store.EventRow{}, nil
}

func contractTestServer() *Server {
	now := time.Now().UTC()
	snap := &collectors.Snapshot{
		CollectedAt: now,
		Nodes:       []model.Node{{Name: "node-01", UID: "u1", Ready: "True", Health: "healthy", Conditions: []model.Condition{}}},
		Workloads:   []model.Workload{},
		Pods:        []model.Pod{},
		Services:    []model.Service{},
		Storage:     &model.Storage{Scope: "kubernetes_objects", DrbdDirectHealth: "not_observed", Items: []model.StorageItem{}},
		Backups: &model.Backups{
			Velero:     model.VeleroBackups{Health: "unknown", Locations: []model.BackupStorageLocation{}, Backups: []model.BackupRecord{}, Restores: []model.BackupRecord{}},
			Postgresql: model.PostgresBackups{Cluster: "portal-db", ObjectStore: "portal-db-backup", Health: "unknown", ExpectedSchedule: "0 0 2 * * *", ExpectedTarget: "prefer-standby", Backups: []model.BackupRecord{}, Wal: model.Wal{State: "unknown", ExpectedArchiveTimeoutSeconds: 300}, Barman: model.BarmanSample{Scope: "single_exporter_sample"}},
			PolicyGaps: policyGaps(),
		},
		Database: &model.Database{Namespace: "portal", Cluster: "portal-db", Health: "unknown",
			Conditions: []model.Condition{},
			HistoricalQualification: model.HistoricalQualification{Scope: "historical_P8B_evidence", Date: "2026-10-20", LatestRestore: "PASS", Pitr: "PASS", IsLiveRecoveryTest: false}},
		Metrics:  []model.Metric{},
		Sources:  []model.SourceStatus{},
		Warnings: []model.Warning{},
	}
	sum := sha256.Sum256([]byte("test-password"))
	verifier, _ := auth.NewVerifier("portal-operator", hex.EncodeToString(sum[:]))
	return &Server{
		collector: mockSnapshotProvider{snap},
		store:     mockStore{},
		verifier:  verifier,
		cfg:       &config.Config{SourceRevision: strings.Repeat("a", 40)},
		rate:      newTokenBucket(1000),
		sem:       make(chan struct{}, 20),
	}
}

func doGet(t *testing.T, h http.Handler, path string) (int, map[string]any) {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, path, nil)
	req.SetBasicAuth("portal-operator", "test-password")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	var m map[string]any
	if err := json.Unmarshal(rr.Body.Bytes(), &m); err != nil {
		t.Fatalf("%s: invalid JSON: %v", path, err)
	}
	return rr.Code, m
}

func TestAllElevenHandlers(t *testing.T) {
	srv := contractTestServer()
	h := srv.Handler()
	paths := []string{
		"/api/v1/health", "/api/v1/summary", "/api/v1/nodes", "/api/v1/workloads",
		"/api/v1/pods", "/api/v1/services", "/api/v1/storage", "/api/v1/backups",
		"/api/v1/database", "/api/v1/metrics", "/api/v1/events",
	}
	for _, p := range paths {
		code, m := doGet(t, h, p)
		if code != http.StatusOK {
			t.Fatalf("%s: expected 200, got %d (%v)", p, code, m)
		}
		for _, k := range []string{"requestId", "generatedAt", "observedAt", "freshness", "partial", "sources", "data", "warnings", "nextCursor"} {
			if _, ok := m[k]; !ok {
				t.Fatalf("%s: envelope missing %q", p, k)
			}
		}
		if m["sources"] == nil {
			t.Fatalf("%s: sources must be non-null array", p)
		}
		if m["warnings"] == nil {
			t.Fatalf("%s: warnings must be non-null array", p)
		}
		if m["data"] == nil {
			t.Fatalf("%s: data must be non-null", p)
		}
	}
}

func TestDataShapes(t *testing.T) {
	srv := contractTestServer()
	h := srv.Handler()
	// nodes data.items
	_, m := doGet(t, h, "/api/v1/nodes")
	if _, ok := m["data"].(map[string]any)["items"]; !ok {
		t.Fatal("nodes data missing items")
	}
	// summary data.overall + counts + subsystems + alerts + coverage
	_, m = doGet(t, h, "/api/v1/summary")
	d := m["data"].(map[string]any)
	for _, k := range []string{"overall", "counts", "subsystems", "alerts", "coverage"} {
		if _, ok := d[k]; !ok {
			t.Fatalf("summary data missing %q", k)
		}
	}
	// backups data.velero/postgresql/policyGaps
	_, m = doGet(t, h, "/api/v1/backups")
	d = m["data"].(map[string]any)
	for _, k := range []string{"velero", "postgresql", "policyGaps"} {
		if _, ok := d[k]; !ok {
			t.Fatalf("backups data missing %q", k)
		}
	}
	// events data.storage/auditComplete/items
	_, m = doGet(t, h, "/api/v1/events")
	d = m["data"].(map[string]any)
	for _, k := range []string{"storage", "auditComplete", "items"} {
		if _, ok := d[k]; !ok {
			t.Fatalf("events data missing %q", k)
		}
	}
}

func TestErrorResponses(t *testing.T) {
	srv := contractTestServer()
	h := srv.Handler()

	// 404 unknown path
	code, m := doGet(t, h, "/api/v1/does-not-exist")
	if code != http.StatusNotFound || m["code"] != "NOT_FOUND" {
		t.Fatalf("expected 404 NOT_FOUND, got %d %v", code, m)
	}
	// 401 unauthenticated
	req := httptest.NewRequest(http.MethodGet, "/api/v1/nodes", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", rr.Code)
	}
	if rr.Header().Get("WWW-Authenticate") == "" {
		t.Fatal("401 missing WWW-Authenticate")
	}
	// 405 wrong method
	req = httptest.NewRequest(http.MethodPost, "/api/v1/nodes", nil)
	req.SetBasicAuth("portal-operator", "test-password")
	rr = httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", rr.Code)
	}
	if rr.Header().Get("Allow") == "" {
		t.Fatal("405 missing Allow header")
	}
	// 400 invalid query
	_, m = doGet(t, h, "/api/v1/nodes?limit=999")
	if m["code"] != "BAD_REQUEST" {
		t.Fatalf("expected BAD_REQUEST, got %v", m["code"])
	}
}
