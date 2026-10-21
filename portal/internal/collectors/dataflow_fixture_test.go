package collectors

import (
	"context"
	"encoding/json"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// Executed by tools/test-dataflow.sh; these are synthetic API fixtures, never
// live PAK observations. Real clients/collectors perform serialization/mapping.
func TestExportCollectorDataflow(t *testing.T) {
	dir := os.Getenv("PORTAL_FIXTURE_DIR")
	if dir == "" {
		t.Skip("run tools/test-dataflow.sh for collector -> handler -> DOM evidence")
	}
	now := time.Now().UTC()
	server := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		for _, tc := range categories() {
			if r.URL.Path == tc.path {
				item := fixtureItem(tc, 0)
				if tc.kind == "Node" {
					item["status"] = map[string]any{"conditions": []any{map[string]any{"type": "Ready", "status": "True"}, map[string]any{"type": "MemoryPressure", "status": "True"}}}
				}
				if strings.Contains(tc.path, "velero") {
					item["status"] = map[string]any{"phase": "Failed"}
				}
				if tc.kind == "NodeMetrics" || tc.kind == "PodMetrics" {
					item["timestamp"] = now.Format(time.RFC3339)
				}
				json.NewEncoder(w).Encode(map[string]any{"apiVersion": tc.api, "kind": tc.kind + "List", "metadata": map[string]any{}, "items": []any{item}})
				return
			}
		}
		obj := map[string]any{"apiVersion": "postgresql.cnpg.io/v1", "kind": "Cluster", "metadata": map[string]any{"namespace": "portal", "name": "portal-db"}, "spec": map[string]any{"instances": 3}, "status": map[string]any{"instances": 3, "readyInstances": 3, "currentPrimary": "portal-db-2", "phase": "Cluster in healthy state", "conditions": []any{map[string]any{"type": "Ready", "status": "True"}, map[string]any{"type": "ContinuousArchiving", "status": "True"}}}}
		if strings.Contains(r.URL.Path, "scheduledbackups") {
			obj["kind"] = "ScheduledBackup"
			obj["spec"] = map[string]any{"schedule": "0 0 2 * * *", "target": "prefer-standby"}
		}
		json.NewEncoder(w).Encode(obj)
	}))
	defer server.Close()
	metrics := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("barman_cloud_cloudnative_pg_io_first_recoverability_point 1792469710\nbarman_cloud_cloudnative_pg_io_last_available_backup_timestamp 1792469800\nbarman_cloud_cloudnative_pg_io_last_failed_backup_timestamp 0\n"))
	}))
	defer metrics.Close()
	cfg := &rest.Config{Host: server.URL, TLSClientConfig: rest.TLSClientConfig{Insecure: true}, QPS: 100, Burst: 100}
	cfg.WrapTransport = func(rt http.RoundTripper) http.RoundTripper { return newGuardTransport(rt, server.URL) }
	typed, err := kubernetes.NewForConfig(cfg)
	if err != nil {
		t.Fatal(err)
	}
	dyn, err := dynamic.NewForConfig(cfg)
	if err != nil {
		t.Fatal(err)
	}
	c := &Collector{clients: &clients{typed: typed, dynamic: dyn}, namespace: "portal", metricsURL: metrics.URL}
	c.collect(context.Background())
	s := c.Latest()
	if s.Backups.Postgresql.Barman.FirstRecoverabilityPointTimestamp == nil || *s.Backups.Postgresql.Barman.FirstRecoverabilityPointTimestamp != 1792469710 {
		t.Fatal("Barman sample not handed to API DTO")
	}
	if s.Backups.Postgresql.Wal.State != "healthy" || s.Backups.Postgresql.Wal.ContinuousArchiving == nil {
		t.Fatal("WAL DTO missing")
	}
	if s.Backups.Velero.Health == "healthy" {
		t.Fatal("Failed Velero objects reported healthy")
	}
	for _, m := range s.Metrics {
		if m.WindowSeconds != 30 {
			t.Fatal("duration window not parsed")
		}
	}
	if s.Nodes[0].Health == "healthy" {
		t.Fatal("pressure ignored")
	}
	b, err := json.Marshal(s)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(dir, "collector-snapshot.json"), b, 0600); err != nil {
		t.Fatal(err)
	}
}
