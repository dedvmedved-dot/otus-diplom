package collectors

import (
	"context"
	"encoding/json"
	"fmt"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
	"time"
)

type categoryCase struct {
	path, kind, api string
	collect         func(*Collector, context.Context, *Snapshot, *SourceRegistry)
	count           func(*Snapshot) int
}

func categories() []categoryCase {
	cases := []categoryCase{
		{"/api/v1/nodes", "Node", "v1", (*Collector).collectNodes, func(s *Snapshot) int { return len(s.Nodes) }},
		{"/api/v1/pods", "Pod", "v1", (*Collector).collectPods, func(s *Snapshot) int { return len(s.Pods) }},
		{"/api/v1/services", "Service", "v1", (*Collector).collectServices, func(s *Snapshot) int { return len(s.Services) }},
		{"/apis/discovery.k8s.io/v1/endpointslices", "EndpointSlice", "discovery.k8s.io/v1", (*Collector).collectServices, func(s *Snapshot) int {
			if len(s.Services) > 0 && s.Services[0].ReadyEndpoints != nil {
				return int(*s.Services[0].ReadyEndpoints)
			}
			return 0
		}},
		{"/api/v1/events", "Event", "v1", (*Collector).collectEvents, func(s *Snapshot) int { return len(s.Events) }},
	}
	for _, pair := range [][3]string{{"deployments", "Deployment", "apps/v1"}, {"statefulsets", "StatefulSet", "apps/v1"}, {"daemonsets", "DaemonSet", "apps/v1"}, {"replicasets", "ReplicaSet", "apps/v1"}, {"jobs", "Job", "batch/v1"}, {"cronjobs", "CronJob", "batch/v1"}} {
		cases = append(cases, categoryCase{"/apis/" + pair[2] + "/" + pair[0], pair[1], pair[2], (*Collector).collectWorkloads, func(s *Snapshot) int { return len(s.Workloads) }})
	}
	for _, pair := range [][3]string{{"/api/v1/persistentvolumeclaims", "PersistentVolumeClaim", "v1"}, {"/api/v1/persistentvolumes", "PersistentVolume", "v1"}, {"/apis/storage.k8s.io/v1/storageclasses", "StorageClass", "storage.k8s.io/v1"}, {"/apis/snapshot.storage.k8s.io/v1/volumesnapshots", "VolumeSnapshot", "snapshot.storage.k8s.io/v1"}} {
		cases = append(cases, categoryCase{pair[0], pair[1], pair[2], (*Collector).collectStorage, func(s *Snapshot) int { return len(s.Storage.Items) }})
	}
	cases = append(cases,
		categoryCase{"/apis/velero.io/v1/namespaces/velero/backupstoragelocations", "BackupStorageLocation", "velero.io/v1", (*Collector).collectBackups, func(s *Snapshot) int { return len(s.Backups.Velero.Locations) }},
		categoryCase{"/apis/velero.io/v1/namespaces/velero/backups", "Backup", "velero.io/v1", (*Collector).collectBackups, func(s *Snapshot) int { return len(s.Backups.Velero.Backups) }},
		categoryCase{"/apis/velero.io/v1/namespaces/velero/restores", "Restore", "velero.io/v1", (*Collector).collectBackups, func(s *Snapshot) int { return len(s.Backups.Velero.Restores) }},
		categoryCase{"/apis/postgresql.cnpg.io/v1/namespaces/portal/backups", "Backup", "postgresql.cnpg.io/v1", (*Collector).collectBackups, func(s *Snapshot) int { return len(s.Backups.Postgresql.Backups) }},
	)
	for _, kind := range []string{"Node", "Pod"} {
		cases = append(cases, categoryCase{"/apis/metrics.k8s.io/v1beta1/" + strings.ToLower(kind) + "s", kind + "Metrics", "metrics.k8s.io/v1beta1", (*Collector).collectMetrics, func(s *Snapshot) int { return len(s.Metrics) }})
	}
	return cases
}
func fixtureItem(tc categoryCase, i int) map[string]any {
	return map[string]any{"apiVersion": tc.api, "kind": tc.kind,
		"metadata": map[string]any{"name": fmt.Sprintf("fixture-%04d", i), "namespace": "portal", "uid": fmt.Sprintf("uid-%d", i), "resourceVersion": "1", "labels": map[string]any{"kubernetes.io/service-name": "probe"}},
		"spec":     map[string]any{"type": "ClusterIP"}, "status": map[string]any{},
		"addressType": "IPv4", "endpoints": []any{map[string]any{"addresses": []string{"10.1.1.1"}, "conditions": map[string]any{"ready": true}}},
		"timestamp": "2026-10-21T00:00:00Z", "window": "30s", "usage": map[string]any{"cpu": "250m", "memory": "1Mi"},
		"containers": []any{map[string]any{"name": "fixture", "usage": map[string]any{"cpu": "250m", "memory": "1Mi"}}},
		"type":       "Normal", "count": 1, "reason": "Started", "involvedObject": map[string]any{"kind": "Pod", "name": "fixture", "uid": "object-uid"},
	}
}
func TestActualCollectorCategoryBoundaries(t *testing.T) {
	all := categories()
	for _, tc := range all {
		for _, size := range []int{201, 501, -1} {
			t.Run(tc.kind+"/"+tc.api+"/"+strconv.Itoa(size), func(t *testing.T) {
				calls := 0
				server := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
					w.Header().Set("Content-Type", "application/json")
					found := tc
					known := false
					for _, c := range all {
						if r.URL.Path == c.path {
							found = c
							known = true
							break
						}
					}
					if !known {
						json.NewEncoder(w).Encode(map[string]any{"apiVersion": "v1", "kind": "Object", "metadata": map[string]any{"name": "fixture"}})
						return
					}
					items := []any{}
					cont := ""
					if r.URL.Path == tc.path {
						calls++
						if r.URL.Query().Get("limit") != "200" {
							t.Errorf("unbounded List query %s", r.URL.RawQuery)
						}
						offset, _ := strconv.Atoi(r.URL.Query().Get("continue"))
						if size == -1 && offset > 0 {
							w.WriteHeader(503)
							json.NewEncoder(w).Encode(map[string]any{"apiVersion": "v1", "kind": "Status", "status": "Failure", "reason": "ServiceUnavailable", "code": 503})
							return
						}
						total := size
						if total < 0 {
							total = 201
						}
						end := min(offset+200, total)
						for i := offset; i < end; i++ {
							items = append(items, fixtureItem(tc, i))
						}
						if end < total {
							cont = strconv.Itoa(end)
						}
					} else if tc.kind == "EndpointSlice" && found.kind == "Service" {
						item := fixtureItem(found, 0)
						item["metadata"].(map[string]any)["name"] = "probe"
						items = append(items, item)
					}
					json.NewEncoder(w).Encode(map[string]any{"apiVersion": found.api, "kind": found.kind + "List", "metadata": map[string]any{"continue": cont}, "items": items})
				}))
				defer server.Close()
				cfg := &rest.Config{Host: server.URL, TLSClientConfig: rest.TLSClientConfig{Insecure: true}}
				// Synthetic server certificate only; production uses in-cluster CA.
				cfg.WrapTransport = func(rt http.RoundTripper) http.RoundTripper { return newGuardTransport(rt, server.URL) }
				typed, err := kubernetes.NewForConfig(cfg)
				if err != nil {
					t.Fatal(err)
				}
				dyn, err := dynamic.NewForConfig(cfg)
				if err != nil {
					t.Fatal(err)
				}
				c := &Collector{clients: &clients{typed: typed, dynamic: dyn}, namespace: "portal"}
				snap := &Snapshot{CollectedAt: time.Now()}
				reg := &SourceRegistry{}
				tc.collect(c, context.Background(), snap, reg)
				snap.Sources = reg.list()
				snap.finalize()
				if size > 0 {
					if got := tc.count(snap); got != min(size, 500) {
						t.Fatalf("want %d got %d", min(size, 500), got)
					}
				}
				if snap.Partial != (size != 201) {
					t.Fatalf("partial=%v size=%d", snap.Partial, size)
				}
				wantCalls := 2
				if size == 501 {
					wantCalls = 3
				}
				if calls != wantCalls {
					t.Fatalf("want %d real List calls got %d", wantCalls, calls)
				}
				if size == -1 {
					found := false
					for _, source := range snap.Sources {
						if source.State == "error" {
							found = true
						}
					}
					if !found {
						t.Fatal("next-page failure missing from source registry")
					}
				}
			})
		}
	}
}
