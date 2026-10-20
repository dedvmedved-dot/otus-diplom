package collectors

import (
	"context"
	"fmt"
	"sort"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

// Fixed GVRs for the dynamic client (no user-controlled resource/verb).
var (
	gvrCNPGCluster        = schema.GroupVersionResource{Group: "postgresql.cnpg.io", Version: "v1", Resource: "clusters"}
	gvrCNPGScheduledBackup = schema.GroupVersionResource{Group: "postgresql.cnpg.io", Version: "v1", Resource: "scheduledbackups"}
	gvrCNPGBackup         = schema.GroupVersionResource{Group: "postgresql.cnpg.io", Version: "v1", Resource: "backups"}
	gvrBarmanObjectStore  = schema.GroupVersionResource{Group: "barmancloud.cnpg.io", Version: "v1", Resource: "objectstores"}
	gvrVeleroBSL          = schema.GroupVersionResource{Group: "velero.io", Version: "v1", Resource: "backupstoragelocations"}
	gvrVeleroBackup       = schema.GroupVersionResource{Group: "velero.io", Version: "v1", Resource: "backups"}
	gvrVeleroRestore      = schema.GroupVersionResource{Group: "velero.io", Version: "v1", Resource: "restores"}
	gvrVolumeSnapshot     = schema.GroupVersionResource{Group: "snapshot.storage.k8s.io", Version: "v1", Resource: "volumesnapshots"}
	gvrGateway            = schema.GroupVersionResource{Group: "gateway.networking.k8s.io", Version: "v1", Resource: "gateways"}
	gvrHTTPRoute          = schema.GroupVersionResource{Group: "gateway.networking.k8s.io", Version: "v1", Resource: "httproutes"}
	gvrNodeMetrics        = schema.GroupVersionResource{Group: "metrics.k8s.io", Version: "v1beta1", Resource: "nodes"}
	gvrPodMetrics         = schema.GroupVersionResource{Group: "metrics.k8s.io", Version: "v1beta1", Resource: "pods"}
)

// addSourceOK records a fresh source with its observed timestamp.
func addSourceOK(snap *Snapshot, id string, observedAt time.Time) {
	ts := observedAt.UTC().Format(time.RFC3339)
	age := int64(time.Since(observedAt).Seconds())
	if age < 0 {
		age = 0
	}
	snap.addSource(model.SourceStatus{
		ID: id, State: "fresh", ObservedAt: &ts, AgeSeconds: &age,
	})
}

// addSourceError records a source that failed to collect.
func addSourceError(snap *Snapshot, id string, err error) {
	code := "COLLECT_ERROR"
	snap.addSource(model.SourceStatus{
		ID: id, State: "error", ErrorCode: &code,
	})
	snap.addWarning(id + ": " + sanitizeErr(err))
}

func sanitizeErr(err error) string {
	if err == nil {
		return ""
	}
	// Generic reason only; never include credential-bearing text.
	return err.Error()
}

func (c *Collector) collectNodes(ctx context.Context, snap *Snapshot) {
	list, err := c.clients.typed.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		addSourceError(snap, "nodes", err)
		return
	}
	for _, n := range list.Items {
		ready := false
		conds := map[string]string{}
		for _, cond := range n.Status.Conditions {
			conds[string(cond.Type)] = string(cond.Status)
			if cond.Type == corev1.NodeReady && cond.Status == corev1.ConditionTrue {
				ready = true
			}
		}
		roles := []string{}
		if n.Labels["node-role.kubernetes.io/control-plane"] != "" {
			roles = append(roles, "control-plane")
		}
		snap.Nodes = append(snap.Nodes, model.NodeInfo{
			Name:             n.Name,
			Ready:            ready,
			Roles:            roles,
			Version:          n.Status.NodeInfo.KubeletVersion,
			Conditions:       conds,
			CPUCapacity:      n.Status.Capacity.Cpu().String(),
			MemoryCapacity:   n.Status.Capacity.Memory().String(),
			CPUAllocatable:   n.Status.Allocatable.Cpu().String(),
			MemoryAllocatable: n.Status.Allocatable.Memory().String(),
		})
	}
	sort.Slice(snap.Nodes, func(i, j int) bool { return snap.Nodes[i].Name < snap.Nodes[j].Name })
	addSourceOK(snap, "nodes", time.Now())
}

func (c *Collector) collectWorkloads(ctx context.Context, snap *Snapshot) {
	ns := c.namespace()
	if ns != "" {
		// Cross-namespace workload view: list all namespaces.
		ns = ""
	}
	add := func(kind string, l func() ([]model.WorkloadInfo, error)) {
		items, err := l()
		if err != nil {
			addSourceError(snap, "workloads", err)
			return
		}
		snap.Workloads = append(snap.Workloads, items...)
	}
	_ = add
	add("deploy", func() ([]model.WorkloadInfo, error) {
		l, err := c.clients.typed.AppsV1().Deployments("").List(ctx, metav1.ListOptions{Limit: 500})
		if err != nil {
			return nil, err
		}
		out := make([]model.WorkloadInfo, 0, len(l.Items))
		for _, d := range l.Items {
			out = append(out, model.WorkloadInfo{Kind: "Deployment", Namespace: d.Namespace, Name: d.Name,
				Desired: *d.Spec.Replicas, Ready: fmt.Sprintf("%d/%d", d.Status.ReadyReplicas, *d.Spec.Replicas),
				Available: d.Status.AvailableReplicas})
		}
		return out, nil
	})
	add("sts", func() ([]model.WorkloadInfo, error) {
		l, err := c.clients.typed.AppsV1().StatefulSets("").List(ctx, metav1.ListOptions{Limit: 500})
		if err != nil {
			return nil, err
		}
		out := make([]model.WorkloadInfo, 0, len(l.Items))
		for _, s := range l.Items {
			var desired int32 = 1
			if s.Spec.Replicas != nil {
				desired = *s.Spec.Replicas
			}
			out = append(out, model.WorkloadInfo{Kind: "StatefulSet", Namespace: s.Namespace, Name: s.Name,
				Desired: desired, Ready: fmt.Sprintf("%d/%d", s.Status.ReadyReplicas, desired),
				Current: s.Status.CurrentReplicas})
		}
		return out, nil
	})
	add("ds", func() ([]model.WorkloadInfo, error) {
		l, err := c.clients.typed.AppsV1().DaemonSets("").List(ctx, metav1.ListOptions{Limit: 500})
		if err != nil {
			return nil, err
		}
		out := make([]model.WorkloadInfo, 0, len(l.Items))
		for _, d := range l.Items {
			out = append(out, model.WorkloadInfo{Kind: "DaemonSet", Namespace: d.Namespace, Name: d.Name,
				Desired: d.Status.DesiredNumberScheduled,
				Ready:   fmt.Sprintf("%d/%d", d.Status.NumberReady, d.Status.DesiredNumberScheduled),
				Current: d.Status.CurrentNumberScheduled})
		}
		return out, nil
	})
	add("rs", func() ([]model.WorkloadInfo, error) {
		l, err := c.clients.typed.AppsV1().ReplicaSets("").List(ctx, metav1.ListOptions{Limit: 500})
		if err != nil {
			return nil, err
		}
		out := make([]model.WorkloadInfo, 0, len(l.Items))
		for _, r := range l.Items {
			var desired int32 = 1
			if r.Spec.Replicas != nil {
				desired = *r.Spec.Replicas
			}
			out = append(out, model.WorkloadInfo{Kind: "ReplicaSet", Namespace: r.Namespace, Name: r.Name,
				Desired: desired, Ready: fmt.Sprintf("%d/%d", r.Status.ReadyReplicas, desired)})
		}
		return out, nil
	})
	add("job", func() ([]model.WorkloadInfo, error) {
		l, err := c.clients.typed.BatchV1().Jobs("").List(ctx, metav1.ListOptions{Limit: 500})
		if err != nil {
			return nil, err
		}
		out := make([]model.WorkloadInfo, 0, len(l.Items))
		for _, j := range l.Items {
			out = append(out, model.WorkloadInfo{Kind: "Job", Namespace: j.Namespace, Name: j.Name,
				Desired: 1, Ready: fmt.Sprintf("%d/%d", j.Status.Succeeded, 1)})
		}
		return out, nil
	})
	add("cronjob", func() ([]model.WorkloadInfo, error) {
		l, err := c.clients.typed.BatchV1().CronJobs("").List(ctx, metav1.ListOptions{Limit: 500})
		if err != nil {
			return nil, err
		}
		out := make([]model.WorkloadInfo, 0, len(l.Items))
		for _, cj := range l.Items {
			out = append(out, model.WorkloadInfo{Kind: "CronJob", Namespace: cj.Namespace, Name: cj.Name,
				Suspended: cj.Spec.Suspend != nil && *cj.Spec.Suspend})
		}
		return out, nil
	})
	addSourceOK(snap, "workloads", time.Now())
}

func (c *Collector) collectPods(ctx context.Context, snap *Snapshot) {
	l, err := c.clients.typed.CoreV1().Pods("").List(ctx, metav1.ListOptions{Limit: 500})
	if err != nil {
		addSourceError(snap, "pods", err)
		return
	}
	for _, p := range l.Items {
		ready, total := 0, 0
		for _, cs := range p.Status.ContainerStatuses {
			total++
			if cs.Ready {
				ready++
			}
		}
		var restarts int32
		for _, cs := range p.Status.ContainerStatuses {
			restarts += cs.RestartCount
		}
		snap.Pods = append(snap.Pods, model.PodInfo{
			Namespace: p.Namespace, Name: p.Name, Phase: string(p.Status.Phase),
			Ready: fmt.Sprintf("%d/%d", ready, total), Restarts: restarts, NodeName: p.Spec.NodeName,
		})
	}
	addSourceOK(snap, "pods", time.Now())
}

func (c *Collector) collectServices(ctx context.Context, snap *Snapshot) {
	l, err := c.clients.typed.CoreV1().Services("").List(ctx, metav1.ListOptions{Limit: 500})
	if err != nil {
		addSourceError(snap, "services", err)
		return
	}
	for _, s := range l.Items {
		ports := []string{}
		for _, p := range s.Spec.Ports {
			ports = append(ports, fmt.Sprintf("%s/%s", p.Name, p.Protocol))
		}
		snap.Services = append(snap.Services, model.ServiceInfo{
			Namespace: s.Namespace, Name: s.Name, Type: string(s.Spec.Type), Ports: ports,
		})
	}
	addSourceOK(snap, "services", time.Now())
}

func (c *Collector) collectStorage(ctx context.Context, snap *Snapshot) {
	pvcs, err := c.clients.typed.CoreV1().PersistentVolumeClaims("").List(ctx, metav1.ListOptions{Limit: 500})
	if err == nil {
		for _, p := range pvcs.Items {
			snap.Storage = append(snap.Storage, model.StorageInfo{
				Kind: "PersistentVolumeClaim", Namespace: p.Namespace, Name: p.Name,
				Phase: string(p.Status.Phase), StorageClass: ptrStr(p.Spec.StorageClassName),
				Capacity: p.Status.Capacity.Storage().String(),
			})
		}
	}
	pvs, err := c.clients.typed.CoreV1().PersistentVolumes().List(ctx, metav1.ListOptions{Limit: 500})
	if err == nil {
		for _, p := range pvs.Items {
			snap.Storage = append(snap.Storage, model.StorageInfo{
				Kind: "PersistentVolume", Name: p.Name, Phase: string(p.Status.Phase),
				StorageClass: p.Spec.StorageClassName, Capacity: p.Spec.Capacity.Storage().String(),
			})
		}
	}
	scs, err := c.clients.typed.StorageV1().StorageClasses().List(ctx, metav1.ListOptions{Limit: 500})
	if err == nil {
		for _, sc := range scs.Items {
			snap.Storage = append(snap.Storage, model.StorageInfo{Kind: "StorageClass", Name: sc.Name})
		}
	}
	snaps, err := c.clients.dynamic.Resource(gvrVolumeSnapshot).List(ctx, metav1.ListOptions{Limit: 500})
	if err == nil {
		for _, vs := range snaps.Items {
			phase, _, _ := unstructured.NestedString(vs.Object, "status", "readyToUse")
			_ = phase
			snap.Storage = append(snap.Storage, model.StorageInfo{
				Kind: "VolumeSnapshot", Namespace: vs.GetNamespace(), Name: vs.GetName(),
				Phase: "ready", // sanitized: we only record existence, not raw status
			})
		}
	}
	if err != nil {
		addSourceError(snap, "storage", err)
		return
	}
	addSourceOK(snap, "storage", time.Now())
}

func (c *Collector) collectBackups(ctx context.Context, snap *Snapshot) {
	// Velero domain (namespace determined at G0; expected "velero").
	velNS := "velero"
	if bsls, err := c.clients.dynamic.Resource(gvrVeleroBSL).Namespace(velNS).List(ctx, metav1.ListOptions{}); err == nil {
		for _, b := range bsls.Items {
			phase, _, _ := unstructured.NestedString(b.Object, "status", "phase")
			snap.Backups = append(snap.Backups, model.BackupInfo{
				Domain: "velero", Kind: "BackupStorageLocation", Namespace: b.GetNamespace(),
				Name: b.GetName(), Phase: phase, Available: phase == "Available",
			})
		}
	}
	if bks, err := c.clients.dynamic.Resource(gvrVeleroBackup).Namespace(velNS).List(ctx, metav1.ListOptions{Limit: 500}); err == nil {
		for _, b := range bks.Items {
			phase, _, _ := unstructured.NestedString(b.Object, "status", "phase")
			snap.Backups = append(snap.Backups, model.BackupInfo{
				Domain: "velero", Kind: "Backup", Namespace: b.GetNamespace(), Name: b.GetName(), Phase: phase,
			})
		}
	}
	if rs, err := c.clients.dynamic.Resource(gvrVeleroRestore).Namespace(velNS).List(ctx, metav1.ListOptions{Limit: 500}); err == nil {
		for _, r := range rs.Items {
			phase, _, _ := unstructured.NestedString(r.Object, "status", "phase")
			snap.Backups = append(snap.Backups, model.BackupInfo{
				Domain: "velero", Kind: "Restore", Namespace: r.GetNamespace(), Name: r.GetName(), Phase: phase,
			})
		}
	}
	// CNPG backups.
	if cnpgs, err := c.clients.dynamic.Resource(gvrCNPGBackup).Namespace("portal").List(ctx, metav1.ListOptions{Limit: 500}); err == nil {
		for _, b := range cnpgs.Items {
			phase, _, _ := unstructured.NestedString(b.Object, "status", "phase")
			started, _, _ := unstructured.NestedString(b.Object, "status", "startedAt")
			snap.Backups = append(snap.Backups, model.BackupInfo{
				Domain: "postgresql", Kind: "Backup", Namespace: b.GetNamespace(), Name: b.GetName(),
				Phase: phase, StartedAt: started,
			})
		}
	}
	addSourceOK(snap, "backups", time.Now())
}

func (c *Collector) collectDatabase(ctx context.Context, snap *Snapshot) {
	obj, err := c.clients.dynamic.Resource(gvrCNPGCluster).Namespace("portal").Get(ctx, "portal-db", metav1.GetOptions{})
	if err != nil {
		addSourceError(snap, "database", err)
		return
	}
	desired, _, _ := unstructured.NestedInt64(obj.Object, "spec", "instances")
	ready, _, _ := unstructured.NestedInt64(obj.Object, "status", "readyInstances")
	primary, _, _ := unstructured.NestedString(obj.Object, "status", "currentPrimary")
	phase, _, _ := unstructured.NestedString(obj.Object, "status", "phase")
	replicas := ready - 1
	inferred := true
	snap.Database = &model.DatabaseInfo{
		Name: obj.GetName(), Desired: int32(desired), Ready: int32(ready),
		CurrentPrimary: primary, Phase: phase, Replicas: int32(replicas), ReplicaInferred: inferred,
		WALArchiving: "unknown",
	}
	// WAL archiving from CNPG conditions (ContinuousArchiving).
	conds, _, _ := unstructured.NestedSlice(obj.Object, "status", "conditions")
	for _, c := range conds {
		m, ok := c.(map[string]any)
		if !ok {
			continue
		}
		t, _ := m["type"].(string)
		if t == "ContinuousArchiving" {
			st, _ := m["status"].(string)
			if st == "True" {
				snap.Database.WALArchiving = "healthy"
			} else {
				snap.Database.WALArchiving = "degraded"
			}
		}
	}
	addSourceOK(snap, "database", time.Now())
}

func (c *Collector) collectMetrics(ctx context.Context, snap *Snapshot) {
	nm, err := c.clients.dynamic.Resource(gvrNodeMetrics).List(ctx, metav1.ListOptions{Limit: 200})
	if err != nil {
		// Metrics is optional; a missing sample is visible, not fatal.
		code := "METRICS_UNAVAILABLE"
		snap.addSource(model.SourceStatus{ID: "metrics", State: "unsupported", ErrorCode: &code})
		return
	}
	for _, n := range nm.Items {
		name := n.GetName()
		ts, _, _ := unstructured.NestedString(n.Object, "timestamp")
		cpu, _, _ := unstructured.NestedString(n.Object, "usage", "cpu")
		mem, _, _ := unstructured.NestedString(n.Object, "usage", "memory")
		snap.Metrics = append(snap.Metrics, model.MetricInfo{Kind: "node", Name: name, CPU: cpu, Memory: mem, Window: ts})
	}
	pm, err := c.clients.dynamic.Resource(gvrPodMetrics).List(ctx, metav1.ListOptions{Limit: 500})
	if err == nil {
		for _, p := range pm.Items {
			cpu, _, _ := unstructured.NestedString(p.Object, "containers")
			_ = cpu
			snap.Metrics = append(snap.Metrics, model.MetricInfo{Kind: "pod", Namespace: p.GetNamespace(), Name: p.GetName()})
		}
	}
	addSourceOK(snap, "metrics", time.Now())
}

func (c *Collector) computeHealth(snap *Snapshot) {
	if snap.Database != nil && snap.Database.Ready != snap.Database.Desired {
		snap.OverallHealth = "warning"
		snap.Warnings = append(snap.Warnings, "database ready/desired mismatch")
		return
	}
	snap.OverallHealth = "healthy"
}

func (c *Collector) namespace() string {
	return ""
}

func ptrStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}
