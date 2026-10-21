package collectors

import (
	"context"
	"sort"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	discoveryv1 "k8s.io/api/discovery/v1"
	storagev1 "k8s.io/api/storage/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

// Fixed GVRs (no user-controlled resource/verb).
var (
	gvrCNPGCluster         = schema.GroupVersionResource{Group: "postgresql.cnpg.io", Version: "v1", Resource: "clusters"}
	gvrCNPGScheduledBackup = schema.GroupVersionResource{Group: "postgresql.cnpg.io", Version: "v1", Resource: "scheduledbackups"}
	gvrCNPGBackup          = schema.GroupVersionResource{Group: "postgresql.cnpg.io", Version: "v1", Resource: "backups"}
	gvrBarmanObjectStore   = schema.GroupVersionResource{Group: "barmancloud.cnpg.io", Version: "v1", Resource: "objectstores"}
	gvrVeleroBSL           = schema.GroupVersionResource{Group: "velero.io", Version: "v1", Resource: "backupstoragelocations"}
	gvrVeleroBackup        = schema.GroupVersionResource{Group: "velero.io", Version: "v1", Resource: "backups"}
	gvrVeleroRestore       = schema.GroupVersionResource{Group: "velero.io", Version: "v1", Resource: "restores"}
	gvrVolumeSnapshot      = schema.GroupVersionResource{Group: "snapshot.storage.k8s.io", Version: "v1", Resource: "volumesnapshots"}
	gvrGateway             = schema.GroupVersionResource{Group: "gateway.networking.k8s.io", Version: "v1", Resource: "gateways"}
	gvrHTTPRoute           = schema.GroupVersionResource{Group: "gateway.networking.k8s.io", Version: "v1", Resource: "httproutes"}
	gvrNodeMetrics         = schema.GroupVersionResource{Group: "metrics.k8s.io", Version: "v1beta1", Resource: "nodes"}
	gvrPodMetrics          = schema.GroupVersionResource{Group: "metrics.k8s.io", Version: "v1beta1", Resource: "pods"}
)

const (
	listPage  = 200
	listCap   = 500
	backupCap = 500
)

// ---- condition / health helpers -------------------------------------------

func toCondition(obj map[string]any) model.Condition {
	c := model.Condition{}
	if t, ok := obj["type"].(string); ok {
		c.Type = t
	}
	if s, ok := obj["status"].(string); ok {
		c.Status = s
	}
	if r, ok := obj["reason"].(string); ok {
		c.Reason = &r
	}
	if l, ok := obj["lastTransitionTime"].(string); ok {
		c.LastTransitionTime = &l
	}
	if g, ok := obj["observedGeneration"].(int64); ok {
		c.ObservedGeneration = &g
	}
	return c
}

func conditionsFromUnstructured(obj map[string]any) []model.Condition {
	raw, _, _ := unstructured.NestedSlice(obj, "status", "conditions")
	out := make([]model.Condition, 0, len(raw))
	for _, r := range raw {
		m, ok := r.(map[string]any)
		if !ok {
			continue
		}
		out = append(out, toCondition(m))
	}
	return out
}

// nodeHealth derives health from Ready + pressure conditions (truthful, not count-based).
func nodeHealth(ready bool, conds map[corev1.NodeConditionType]corev1.ConditionStatus) string {
	if !ready {
		return "critical"
	}
	if conds[corev1.NodeMemoryPressure] == corev1.ConditionTrue ||
		conds[corev1.NodeDiskPressure] == corev1.ConditionTrue ||
		conds[corev1.NodePIDPressure] == corev1.ConditionTrue {
		return "warning"
	}
	return "healthy"
}

func podHealth(phase corev1.PodPhase, ready, total int) string {
	switch phase {
	case corev1.PodRunning:
		if total > 0 && ready == total {
			return "healthy"
		}
		return "warning"
	case corev1.PodPending:
		return "warning"
	case corev1.PodFailed:
		return "critical"
	case corev1.PodSucceeded:
		return "healthy"
	default:
		return "unknown"
	}
}

func pvcHealth(phase corev1.PersistentVolumeClaimPhase) string {
	switch phase {
	case corev1.ClaimBound:
		return "healthy"
	case corev1.ClaimPending:
		return "warning"
	case corev1.ClaimLost:
		return "critical"
	default:
		return "unknown"
	}
}

func pvHealth(phase corev1.PersistentVolumePhase) string {
	switch phase {
	case corev1.VolumeAvailable, corev1.VolumeBound:
		return "healthy"
	case corev1.VolumePending:
		return "warning"
	case corev1.VolumeFailed, corev1.VolumeReleased:
		return "critical"
	default:
		return "unknown"
	}
}

func backupHealth(phase string) string {
	switch phase {
	case "Completed", "completed", "Available":
		return "healthy"
	case "InProgress", "in-progress", "New", "":
		return "warning"
	case "Failed", "failed", "Deleting":
		return "critical"
	default:
		return "unknown"
	}
}

func condStatus(core *corev1.Node) (bool, map[corev1.NodeConditionType]corev1.ConditionStatus) {
	ready := false
	m := map[corev1.NodeConditionType]corev1.ConditionStatus{}
	for _, c := range core.Status.Conditions {
		m[c.Type] = c.Status
		if c.Type == corev1.NodeReady && c.Status == corev1.ConditionTrue {
			ready = true
		}
	}
	return ready, m
}

// ---- nodes ------------------------------------------------------------------

func (c *Collector) collectNodes(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	nodes, truncated, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]corev1.Node, string, error) {
		l, e := c.clients.typed.CoreV1().Nodes().List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.Continue, nil
	})
	state := "ok"
	if err != nil {
		state = "error"
		snap.setPartial()
	} else if truncated {
		snap.setPartial()
	}
	reg.set(sourceStatus("k8s/nodes", state, now, err))
	for _, n := range nodes {
		ready, conds := condStatus(&n)
		nodeConds := make([]model.Condition, 0, len(n.Status.Conditions))
		for _, cd := range n.Status.Conditions {
			var reason *string
			if cd.Reason != "" {
				reason = &cd.Reason
			}
			var ltt *string
			if !cd.LastTransitionTime.IsZero() {
				v := cd.LastTransitionTime.UTC().Format(time.RFC3339)
				ltt = &v
			}
			nodeConds = append(nodeConds, model.Condition{
				Type: string(cd.Type), Status: string(cd.Status), Reason: reason, LastTransitionTime: ltt,
			})
		}
		snap.Nodes = append(snap.Nodes, model.Node{
			Name: n.Name, UID: string(n.UID), Ready: string(readyStatus(ready)),
			Health: nodeHealth(ready, conds), Conditions: nodeConds,
			CapacityCpuCores:      parseCpuCores(n.Status.Capacity.Cpu().String()),
			AllocatableCpuCores:   parseCpuCores(n.Status.Allocatable.Cpu().String()),
			CapacityMemoryBytes:   parseMemoryBytes(n.Status.Capacity.Memory().String()),
			AllocatableMemoryBytes: parseMemoryBytes(n.Status.Allocatable.Memory().String()),
		})
	}
	sort.Slice(snap.Nodes, func(i, j int) bool { return snap.Nodes[i].Name < snap.Nodes[j].Name })
}

func readyStatus(ready bool) string {
	if ready {
		return "True"
	}
	return "False"
}

// ---- workloads ----------------------------------------------------------------

func (c *Collector) collectWorkloads(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	var errAll error
	partial := false
	appendFrom := func(kind string, f func(opts metav1.ListOptions) ([]model.Workload, string, error)) {
		items, truncated, err := listWithContinue(ctx, listPage, listCap, f)
		if err != nil {
			errAll = err
			return
		}
		if truncated {
			partial = true
		}
		snap.Workloads = append(snap.Workloads, items...)
	}

	appendFrom("Deployment", func(opts metav1.ListOptions) ([]model.Workload, string, error) {
		l, err := c.clients.typed.AppsV1().Deployments("").List(ctx, opts)
		if err != nil {
			return nil, "", err
		}
		out := make([]model.Workload, 0, len(l.Items))
		for _, d := range l.Items {
			var desired, ready int32
			if d.Spec.Replicas != nil {
				desired = *d.Spec.Replicas
			}
			ready = d.Status.ReadyReplicas
			h := "unknown"
			if desired > 0 {
				if ready == desired {
					h = "healthy"
				} else if ready > 0 {
					h = "warning"
				} else {
					h = "critical"
				}
			}
			out = append(out, model.Workload{Name: d.Name, Namespace: d.Namespace, UID: string(d.UID), Kind: "Deployment",
				Health: h, Desired: &desired, Ready: &ready, Conditions: deployConditions(d.Status.Conditions)})
		}
		return out, l.Continue, nil
	})
	appendFrom("StatefulSet", func(opts metav1.ListOptions) ([]model.Workload, string, error) {
		l, err := c.clients.typed.AppsV1().StatefulSets("").List(ctx, opts)
		if err != nil {
			return nil, "", err
		}
		out := make([]model.Workload, 0, len(l.Items))
		for _, s := range l.Items {
			var desired int32 = 1
			if s.Spec.Replicas != nil {
				desired = *s.Spec.Replicas
			}
			ready := s.Status.ReadyReplicas
			h := "unknown"
			if desired > 0 {
				if ready == desired {
					h = "healthy"
				} else if ready > 0 {
					h = "warning"
				} else {
					h = "critical"
				}
			}
			out = append(out, model.Workload{Name: s.Name, Namespace: s.Namespace, UID: string(s.UID), Kind: "StatefulSet",
				Health: h, Desired: &desired, Ready: &ready, Conditions: stsConditions(s.Status.Conditions)})
		}
		return out, l.Continue, nil
	})
	appendFrom("DaemonSet", func(opts metav1.ListOptions) ([]model.Workload, string, error) {
		l, err := c.clients.typed.AppsV1().DaemonSets("").List(ctx, opts)
		if err != nil {
			return nil, "", err
		}
		out := make([]model.Workload, 0, len(l.Items))
		for _, d := range l.Items {
			desired := d.Status.DesiredNumberScheduled
			ready := d.Status.NumberReady
			h := "unknown"
			if desired > 0 {
				if ready == desired {
					h = "healthy"
				} else if ready > 0 {
					h = "warning"
				} else {
					h = "critical"
				}
			}
			out = append(out, model.Workload{Name: d.Name, Namespace: d.Namespace, UID: string(d.UID), Kind: "DaemonSet",
				Health: h, Desired: &desired, Ready: &ready, Conditions: dsConditions(d.Status.Conditions)})
		}
		return out, l.Continue, nil
	})
	appendFrom("ReplicaSet", func(opts metav1.ListOptions) ([]model.Workload, string, error) {
		l, err := c.clients.typed.AppsV1().ReplicaSets("").List(ctx, opts)
		if err != nil {
			return nil, "", err
		}
		out := make([]model.Workload, 0, len(l.Items))
		for _, r := range l.Items {
			var desired int32 = 1
			if r.Spec.Replicas != nil {
				desired = *r.Spec.Replicas
			}
			ready := r.Status.ReadyReplicas
			h := "unknown"
			if desired > 0 {
				if ready == desired {
					h = "healthy"
				} else {
					h = "warning"
				}
			}
			out = append(out, model.Workload{Name: r.Name, Namespace: r.Namespace, UID: string(r.UID), Kind: "ReplicaSet",
				Health: h, Desired: &desired, Ready: &ready})
		}
		return out, l.Continue, nil
	})
	appendFrom("Job", func(opts metav1.ListOptions) ([]model.Workload, string, error) {
		l, err := c.clients.typed.BatchV1().Jobs("").List(ctx, opts)
		if err != nil {
			return nil, "", err
		}
		out := make([]model.Workload, 0, len(l.Items))
		for _, j := range l.Items {
			active := j.Status.Active
			succeeded := j.Status.Succeeded
			failed := j.Status.Failed
			h := "unknown"
			switch {
			case failed > 0:
				h = "critical"
			case succeeded > 0:
				h = "healthy"
			case active > 0:
				h = "warning"
			}
			out = append(out, model.Workload{Name: j.Name, Namespace: j.Namespace, UID: string(j.UID), Kind: "Job",
				Health: h, Active: &active, Succeeded: &succeeded, Failed: &failed})
		}
		return out, l.Continue, nil
	})
	appendFrom("CronJob", func(opts metav1.ListOptions) ([]model.Workload, string, error) {
		l, err := c.clients.typed.BatchV1().CronJobs("").List(ctx, opts)
		if err != nil {
			return nil, "", err
		}
		out := make([]model.Workload, 0, len(l.Items))
		for _, cj := range l.Items {
			var suspended bool
			if cj.Spec.Suspend != nil {
				suspended = *cj.Spec.Suspend
			}
			h := "healthy"
			if suspended {
				h = "warning"
			}
			out = append(out, model.Workload{Name: cj.Name, Namespace: cj.Namespace, UID: string(cj.UID), Kind: "CronJob",
				Health: h, Suspended: &suspended})
		}
		return out, l.Continue, nil
	})

	if partial {
		snap.setPartial()
	}
	state := "ok"
	if errAll != nil {
		state = "error"
		snap.setPartial()
	}
	reg.set(sourceStatus("k8s/workloads", state, now, errAll))
	sort.Slice(snap.Workloads, func(i, j int) bool {
		if snap.Workloads[i].Namespace != snap.Workloads[j].Namespace {
			return snap.Workloads[i].Namespace < snap.Workloads[j].Namespace
		}
		return snap.Workloads[i].Name < snap.Workloads[j].Name
	})
}

func mkCond(typ string, status corev1.ConditionStatus, reason string, ltt metav1.Time) model.Condition {
	var r *string
	if reason != "" {
		r = &reason
	}
	var lt *string
	if !ltt.IsZero() {
		v := ltt.UTC().Format(time.RFC3339)
		lt = &v
	}
	return model.Condition{Type: typ, Status: string(status), Reason: r, LastTransitionTime: lt}
}

func deployConditions(conds []appsv1.DeploymentCondition) []model.Condition {
	out := make([]model.Condition, 0, len(conds))
	for _, c := range conds {
		out = append(out, mkCond(string(c.Type), c.Status, c.Reason, c.LastTransitionTime))
	}
	return out
}

func stsConditions(conds []appsv1.StatefulSetCondition) []model.Condition {
	out := make([]model.Condition, 0, len(conds))
	for _, c := range conds {
		out = append(out, mkCond(string(c.Type), c.Status, c.Reason, c.LastTransitionTime))
	}
	return out
}

func dsConditions(conds []appsv1.DaemonSetCondition) []model.Condition {
	out := make([]model.Condition, 0, len(conds))
	for _, c := range conds {
		out = append(out, mkCond(string(c.Type), c.Status, c.Reason, c.LastTransitionTime))
	}
	return out
}

// ---- pods ---------------------------------------------------------------------

func (c *Collector) collectPods(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	pods, truncated, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]corev1.Pod, string, error) {
		l, e := c.clients.typed.CoreV1().Pods("").List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.Continue, nil
	})
	state := "ok"
	if err != nil {
		state = "error"
		snap.setPartial()
	} else if truncated {
		snap.setPartial()
	}
	reg.set(sourceStatus("k8s/pods", state, now, err))
	for _, p := range pods {
		ready, total := 0, 0
		var restarts int32
		for _, cs := range p.Status.ContainerStatuses {
			total++
			if cs.Ready {
				ready++
			}
			restarts += cs.RestartCount
		}
		var nodeName *string
		if p.Spec.NodeName != "" {
			nodeName = &p.Spec.NodeName
		}
		snap.Pods = append(snap.Pods, model.Pod{
			Name: p.Name, Namespace: p.Namespace, UID: string(p.UID), NodeName: nodeName,
			Phase: string(p.Status.Phase), ReadyContainers: int32(ready), TotalContainers: int32(total),
			RestartCount: restarts, Health: podHealth(p.Status.Phase, ready, total),
		})
	}
}

// ---- services --------------------------------------------------------------------

func (c *Collector) collectServices(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	svcs, truncated, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]corev1.Service, string, error) {
		l, e := c.clients.typed.CoreV1().Services("").List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.Continue, nil
	})
	state := "ok"
	if err != nil {
		state = "error"
		snap.setPartial()
	} else if truncated {
		snap.setPartial()
	}
	reg.set(sourceStatus("k8s/services", state, now, err))

	// EndpointSlice ready counts, keyed by "namespace/name".
	readyByService := map[string]int32{}
	slices, slicesTruncated, serr := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]discoveryv1.EndpointSlice, string, error) {
		l, e := c.clients.typed.DiscoveryV1().EndpointSlices("").List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.Continue, nil
	})
	if serr != nil {
		snap.addWarning(model.Warning{Code: "ENDPOINTSLICES_UNAVAILABLE", Severity: "warning",
			Message: "endpointslices read failed; readyEndpoints unknown", Source: "k8s/endpointslices"})
	} else {
		if slicesTruncated {
			snap.setPartial()
		}
		for _, es := range slices {
			svcName := es.Labels["kubernetes.io/service-name"]
			if svcName == "" {
				continue
			}
			key := es.Namespace + "/" + svcName
			for _, ep := range es.Endpoints {
				if ep.Conditions.Ready != nil && *ep.Conditions.Ready {
					readyByService[key]++
				}
			}
		}
	}

	for _, s := range svcs {
		ports := make([]model.ServicePort, 0, len(s.Spec.Ports))
		for _, p := range s.Spec.Ports {
			var name *string
			if p.Name != "" {
				name = &p.Name
			}
			ports = append(ports, model.ServicePort{Name: name, Port: p.Port, Protocol: string(p.Protocol)})
		}
		key := s.Namespace + "/" + s.Name
		var ready *int32
		if v, ok := readyByService[key]; ok {
			ready = &v
		}
		h := "unknown"
		if ready != nil {
			if *ready > 0 {
				h = "healthy"
			} else {
				h = "warning"
			}
		}
		snap.Services = append(snap.Services, model.Service{
			Name: s.Name, Namespace: s.Namespace, UID: string(s.UID), Type: string(s.Spec.Type),
			Ports: ports, ReadyEndpoints: ready, Health: h,
		})
	}
}

// ---- storage ----------------------------------------------------------------------

func (c *Collector) collectStorage(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	items := []model.StorageItem{}
	partial := false
	var errAll error

	pvcs, truncatedPVC, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]corev1.PersistentVolumeClaim, string, error) {
		l, e := c.clients.typed.CoreV1().PersistentVolumeClaims("").List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.Continue, nil
	})
	if err != nil {
		errAll = err
	} else {
		if truncatedPVC {
			partial = true
		}
		for _, p := range pvcs {
			ns := p.Namespace
			phase := string(p.Status.Phase)
			var sc *string
			if p.Spec.StorageClassName != nil {
				sc = p.Spec.StorageClassName
			}
			cap := parseMemoryBytes(p.Status.Capacity.Storage().String())
			req := parseMemoryBytes(p.Spec.Resources.Requests.Storage().String())
			items = append(items, model.StorageItem{Kind: "PersistentVolumeClaim", Name: p.Name, Namespace: &ns,
				UID: string(p.UID), Phase: &phase, StorageClass: sc, CapacityBytes: cap, RequestedBytes: req,
				Health: pvcHealth(p.Status.Phase)})
		}
	}

	pvs, truncatedPV, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]corev1.PersistentVolume, string, error) {
		l, e := c.clients.typed.CoreV1().PersistentVolumes().List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.Continue, nil
	})
	if err != nil {
		errAll = err
	} else {
		if truncatedPV {
			partial = true
		}
		for _, p := range pvs {
			phase := string(p.Status.Phase)
			cap := parseMemoryBytes(p.Spec.Capacity.Storage().String())
			items = append(items, model.StorageItem{Kind: "PersistentVolume", Name: p.Name, UID: string(p.UID),
				Phase: &phase, StorageClass: &p.Spec.StorageClassName, CapacityBytes: cap, Health: pvHealth(p.Status.Phase)})
		}
	}

	scs, truncatedSC, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]storagev1.StorageClass, string, error) {
		l, e := c.clients.typed.StorageV1().StorageClasses().List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.Continue, nil
	})
	if err != nil {
		errAll = err
	} else {
		if truncatedSC {
			partial = true
		}
		for _, sc := range scs {
			items = append(items, model.StorageItem{Kind: "StorageClass", Name: sc.Name, UID: string(sc.UID), Health: "unknown"})
		}
	}

	snaps, truncatedSnap, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]unstructured.Unstructured, string, error) {
		l, e := c.clients.dynamic.Resource(gvrVolumeSnapshot).List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.GetContinue(), nil
	})
	if err != nil {
		code := classifyError(err)
		reg.set(model.SourceStatus{ID: "k8s/volumesnapshots", State: "error", ErrorCode: &code,
			ObservedAt: nowPtr(), AgeSeconds: f64p(0)})
	} else {
		if truncatedSnap {
			partial = true
		}
		for _, vs := range snaps {
			ns := vs.GetNamespace()
			var ready *bool
			if r, found, _ := unstructured.NestedBool(vs.Object, "status", "readyToUse"); found {
				ready = &r
			}
			var created *string
			if ct, found, _ := unstructured.NestedString(vs.Object, "status", "creationTime"); found {
				created = &ct
			}
			items = append(items, model.StorageItem{Kind: "VolumeSnapshot", Name: vs.GetName(), Namespace: &ns,
				UID: string(vs.GetUID()), SnapshotReadyToUse: ready, SnapshotCreationTime: created,
				Health: snapshotHealth(ready)})
		}
		reg.set(sourceStatus("k8s/volumesnapshots", "ok", now, nil))
	}

	if partial {
		snap.setPartial()
	}
	state := "ok"
	if errAll != nil {
		state = "error"
		snap.setPartial()
	}
	reg.set(sourceStatus("k8s/storage", state, now, errAll))
	snap.Storage = &model.Storage{Scope: "kubernetes_objects", DrbdDirectHealth: "not_observed", Items: items}
}

func snapshotHealth(ready *bool) string {
	if ready == nil {
		return "unknown"
	}
	if *ready {
		return "healthy"
	}
	return "warning"
}

func f64p(v float64) *float64 { return &v }

// parseDurationSeconds converts a metrics-server "window" duration string (e.g.
// "30s") to float64 seconds. Returns 0 for empty/unparseable input.
func parseDurationSeconds(s string) float64 {
	if s == "" {
		return 0
	}
	d, err := time.ParseDuration(s)
	if err != nil {
		return 0
	}
	return d.Seconds()
}

// ---- backups -----------------------------------------------------------------------

func (c *Collector) collectBackups(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	velNS := "velero"
	velero := model.VeleroBackups{Locations: []model.BackupStorageLocation{}, Backups: []model.BackupRecord{}, Restores: []model.BackupRecord{}}
	pg := model.PostgresBackups{
		Cluster: "portal-db", ObjectStore: "portal-db-backup",
		ExpectedSchedule: "0 0 2 * * *", ExpectedTarget: "prefer-standby",
		Backups: []model.BackupRecord{}, Wal: model.Wal{State: "unknown", ExpectedArchiveTimeoutSeconds: 300, MeasuredRpoSeconds: nil},
		Barman: model.BarmanSample{Scope: "single_exporter_sample"},
	}
	veleroTruncated, pgTruncated := false, false
	var veleroErr, pgErr error

	// Velero BSL
	bsl, bslTruncated, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]unstructured.Unstructured, string, error) {
		l, e := c.clients.dynamic.Resource(gvrVeleroBSL).Namespace(velNS).List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.GetContinue(), nil
	})
	if err != nil {
		veleroErr = err
		reg.set(sourceStatus("velero/bsl", "error", now, err))
	} else {
		if bslTruncated {
			veleroTruncated = true
		}
		for _, b := range bsl {
			phase, _, _ := unstructured.NestedString(b.Object, "status", "phase")
			var lvt *string
			if v, found, _ := unstructured.NestedString(b.Object, "status", "lastValidationTime"); found {
				lvt = &v
			}
			velero.Locations = append(velero.Locations, model.BackupStorageLocation{
				Name: b.GetName(), Namespace: b.GetNamespace(), Phase: strPtrOrNil(phase),
				LastValidationTime: lvt, Health: backupHealth(phase),
			})
		}
		reg.set(sourceStatus("velero/bsl", "ok", now, nil))
	}

	// Velero backups
	if backups, trunc, err := listWithContinue(ctx, listPage, backupCap, func(opts metav1.ListOptions) ([]unstructured.Unstructured, string, error) {
		l, e := c.clients.dynamic.Resource(gvrVeleroBackup).Namespace(velNS).List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.GetContinue(), nil
	}); err != nil {
		veleroErr = err
		reg.set(sourceStatus("velero/backups", "error", now, err))
	} else {
		if trunc {
			veleroTruncated = true
		}
		for _, b := range backups {
			velero.Backups = append(velero.Backups, backupRecordFrom(b.Object))
		}
		reg.set(sourceStatus("velero/backups", "ok", now, nil))
	}

	// Velero restores
	if restores, trunc, err := listWithContinue(ctx, listPage, backupCap, func(opts metav1.ListOptions) ([]unstructured.Unstructured, string, error) {
		l, e := c.clients.dynamic.Resource(gvrVeleroRestore).Namespace(velNS).List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.GetContinue(), nil
	}); err != nil {
		veleroErr = err
		reg.set(sourceStatus("velero/restores", "error", now, err))
	} else {
		if trunc {
			veleroTruncated = true
		}
		for _, b := range restores {
			velero.Restores = append(velero.Restores, backupRecordFrom(b.Object))
		}
		reg.set(sourceStatus("velero/restores", "ok", now, nil))
	}

	// CNPG backups
	if cbackups, trunc, err := listWithContinue(ctx, listPage, backupCap, func(opts metav1.ListOptions) ([]unstructured.Unstructured, string, error) {
		l, e := c.clients.dynamic.Resource(gvrCNPGBackup).Namespace("portal").List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.GetContinue(), nil
	}); err != nil {
		pgErr = err
		reg.set(sourceStatus("cnpg/backups", "error", now, err))
	} else {
		if trunc {
			pgTruncated = true
		}
		for _, b := range cbackups {
			rec := backupRecordFrom(b.Object)
			pg.Backups = append(pg.Backups, rec)
			if rec.Phase != nil && (*rec.Phase == "completed" || *rec.Phase == "Completed") && rec.CompletedAt != nil {
				if pg.LastSuccessfulBackupAt == nil || (rec.CompletedAt != nil && *rec.CompletedAt > *pg.LastSuccessfulBackupAt) {
					pg.LastSuccessfulBackupAt = rec.CompletedAt
				}
			}
		}
		pg.SuccessfulBackupsObserved = int32(countSuccessful(pg.Backups))
		reg.set(sourceStatus("cnpg/backups", "ok", now, nil))
	}

	// ScheduledBackup + ObjectStore named GET
	collectPGNamed(ctx, c, &pg, reg, now)

	veleroHealths := []string{}
	if veleroErr != nil {
		veleroHealths = append(veleroHealths, "critical")
	}
	for _, loc := range velero.Locations {
		veleroHealths = append(veleroHealths, loc.Health)
	}
	veleroHealths = append(veleroHealths, backupAggregateHealth(velero.Backups))
	veleroHealths = append(veleroHealths, backupAggregateHealth(velero.Restores))
	velero.Health = aggregateHealth(veleroHealths)
	velero.CollectionTruncated = veleroTruncated
	pg.CollectionTruncated = pgTruncated
	if pgErr != nil {
		pg.Health = "critical"
	} else {
		pg.Health = aggregateHealth([]string{backupAggregateHealth(pg.Backups)})
	}

	snap.Backups = &model.Backups{Velero: velero, Postgresql: pg, PolicyGaps: policyGaps()}
	if veleroErr != nil || pgErr != nil {
		snap.setPartial()
	}
	if veleroTruncated || pgTruncated {
		snap.setPartial()
	}
}

func backupRecordFrom(obj map[string]any) model.BackupRecord {
	phase, _, _ := unstructured.NestedString(obj, "status", "phase")
	var started, completed *string
	if v, found, _ := unstructured.NestedString(obj, "status", "startTimestamp"); found {
		started = &v
	}
	if v, found, _ := unstructured.NestedString(obj, "status", "completionTimestamp"); found {
		completed = &v
	}
	var warnings, errors *int32
	if v, found, _ := unstructured.NestedInt64(obj, "status", "warnings"); found {
		w := int32(v)
		warnings = &w
	}
	if v, found, _ := unstructured.NestedInt64(obj, "status", "errors"); found {
		e := int32(v)
		errors = &e
	}
	return model.BackupRecord{
		Name: getString(obj, "metadata", "name"), Namespace: getString(obj, "metadata", "namespace"),
		Phase: strPtrOrNil(phase), StartedAt: started, CompletedAt: completed,
		WarningsCount: warnings, ErrorsCount: errors, Health: backupHealth(phase),
	}
}

func countSuccessful(recs []model.BackupRecord) int {
	n := 0
	for _, r := range recs {
		if r.Phase != nil && (*r.Phase == "completed" || *r.Phase == "Completed") {
			n++
		}
	}
	return n
}

func collectPGNamed(ctx context.Context, c *Collector, pg *model.PostgresBackups, reg *SourceRegistry, now time.Time) {
	// ScheduledBackup portal-db-daily
	if sb, err := c.clients.dynamic.Resource(gvrCNPGScheduledBackup).Namespace("portal").Get(ctx, "portal-db-daily", metav1.GetOptions{}); err != nil {
		reg.set(sourceStatus("cnpg/scheduledbackups", "error", now, err))
	} else {
		pg.ScheduledBackupObserved = true
		sched, _, _ := unstructured.NestedString(sb.Object, "spec", "schedule")
		target, _, _ := unstructured.NestedString(sb.Object, "spec", "target")
		pg.Schedule = strPtrOrNil(sched)
		pg.Target = strPtrOrNil(target)
		reg.set(sourceStatus("cnpg/scheduledbackups", "ok", now, nil))
	}
	// ObjectStore portal-db-backup
	if _, err := c.clients.dynamic.Resource(gvrBarmanObjectStore).Namespace("portal").Get(ctx, "portal-db-backup", metav1.GetOptions{}); err != nil {
		reg.set(sourceStatus("barman/objectstores", "error", now, err))
	} else {
		reg.set(sourceStatus("barman/objectstores", "ok", now, nil))
	}
}

func aggregateHealth(healths []string) string {
	hasCritical, hasWarning, hasUnknown := false, false, false
	hasAny := false
	for _, h := range healths {
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

func healthFromErr(err error) string {
	if err != nil {
		return "critical"
	}
	return "healthy"
}

func backupAggregateHealth(recs []model.BackupRecord) string {
	hs := make([]string, 0, len(recs))
	for _, r := range recs {
		hs = append(hs, r.Health)
	}
	return aggregateHealth(hs)
}

func policyGaps() []model.PolicyGap {
	return []model.PolicyGap{
		{ID: "TR_PG_WAL_14D", Status: "IMPLEMENTED_POLICY", Explanation: "WAL archiving enabled; retention 14d in ObjectStore."},
		{ID: "TR_PG_FULL_8_COPIES", Status: "POLICY_CAPABLE_NOT_TIME_AGED", Explanation: "Daily schedule capable of >=8 full copies; not yet time-aged."},
		{ID: "TR_PG_INCREMENTAL_DIFFERENTIAL_14", Status: "NOT_IMPLEMENTED_IN_SELECTED_PLUGIN_PATH", Explanation: "Barman Cloud Plugin path does not implement incremental/differential."},
		{ID: "TR_MONTHLY_CONTROL_12", Status: "DEFERRED_TO_P8G_P9_POLICY_CLOSURE", Explanation: "Deferred to P8G/P9 policy closure."},
	}
}

// ---- database -----------------------------------------------------------------------

func (c *Collector) collectDatabase(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	obj, err := c.clients.dynamic.Resource(gvrCNPGCluster).Namespace("portal").Get(ctx, "portal-db", metav1.GetOptions{})
	if err != nil {
		reg.set(sourceStatus("cnpg/cluster", "error", now, err))
		snap.setPartial()
		return
	}
	reg.set(sourceStatus("cnpg/cluster", "ok", now, nil))

	var desired, ready *int32
	if v, found, _ := unstructured.NestedInt64(obj.Object, "spec", "instances"); found {
		d := int32(v)
		desired = &d
	}
	if v, found, _ := unstructured.NestedInt64(obj.Object, "status", "readyInstances"); found {
		r := int32(v)
		ready = &r
	}
	primary, _, _ := unstructured.NestedString(obj.Object, "status", "currentPrimary")
	phase, _, _ := unstructured.NestedString(obj.Object, "status", "phase")

	// Replicas: ready - 1 only if ready>0, marked inferred (not an observed count).
	replicasInferred := true
	var replicas *int32
	if ready != nil && *ready > 0 {
		r := *ready - 1
		replicas = &r
	} else {
		zero := int32(0)
		replicas = &zero
	}

	conds := conditionsFromUnstructured(obj.Object)
	if conds == nil {
		conds = []model.Condition{}
	}

	// WAL archiving condition.
	walState := "unknown"
	var archCond *model.Condition
	for _, cd := range conds {
		if cd.Type == "ContinuousArchiving" {
			c := cd
			archCond = &c
			if cd.Status == "True" {
				walState = "healthy"
			} else {
				walState = "warning"
			}
		}
	}

	h := "unknown"
	if ready != nil && desired != nil {
		if *ready == *desired && phase == "Cluster in healthy state" {
			h = "healthy"
		} else if *ready > 0 {
			h = "warning"
		} else {
			h = "critical"
		}
	}

	snap.Database = &model.Database{
		Namespace: "portal", Cluster: "portal-db", Health: h,
		DesiredInstances: desired, ReadyInstances: ready,
		PrimaryName: strPtrOrNil(primary), ReplicasObserved: replicas, ReplicasInferred: replicasInferred,
		Phase: strPtrOrNil(phase), Conditions: conds, ApplicationDbConnected: false,
		RecoveryState: nil,
		HistoricalQualification: model.HistoricalQualification{
			Scope: "historical_P8B_evidence", Date: "2026-10-20", LatestRestore: "PASS", Pitr: "PASS",
			IsLiveRecoveryTest: false,
		},
	}
	_ = walState
	_ = archCond
	// Cross-collector handoff to Backups.Postgresql.Wal (consumed in finalize).
	snap.WalState = walState
	if archCond != nil {
		snap.WalArchivingCondition = archCond
	}
}

// ---- metrics ------------------------------------------------------------------------

func (c *Collector) collectMetrics(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	nm, nmTruncated, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]unstructured.Unstructured, string, error) {
		l, e := c.clients.dynamic.Resource(gvrNodeMetrics).List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.GetContinue(), nil
	})
	if err != nil {
		reg.set(sourceStatus("k8s/metrics", "error", now, err))
		snap.setPartial()
		return
	}
	if nmTruncated {
		snap.setPartial()
	}
	for _, n := range nm {
		ts, _, _ := unstructured.NestedString(n.Object, "timestamp")
		windowStr, _, _ := unstructured.NestedString(n.Object, "window")
		cpuStr, _, _ := unstructured.NestedString(n.Object, "usage", "cpu")
		memStr, _, _ := unstructured.NestedString(n.Object, "usage", "memory")
		snap.Metrics = append(snap.Metrics, model.Metric{
			Kind: "Node", Name: n.GetName(), SampleTimestamp: ts,
			WindowSeconds: parseDurationSeconds(windowStr), CpuCores: parseCpuCores(cpuStr), MemoryBytes: parseMemoryBytes(memStr),
		})
	}

	pm, pmTruncated, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]unstructured.Unstructured, string, error) {
		l, e := c.clients.dynamic.Resource(gvrPodMetrics).List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.GetContinue(), nil
	})
	if err != nil {
		reg.set(sourceStatus("k8s/podmetrics", "error", now, err))
	} else {
		if pmTruncated {
			snap.setPartial()
		}
		for _, p := range pm {
			ts, _, _ := unstructured.NestedString(p.Object, "timestamp")
			windowStr, _, _ := unstructured.NestedString(p.Object, "window")
			var cpuMillis, memBytes int64
			containers, _, _ := unstructured.NestedSlice(p.Object, "containers")
			for _, c := range containers {
				cm, ok := c.(map[string]any)
				if !ok {
					continue
				}
				usage, _, _ := unstructured.NestedMap(cm, "usage")
				if cpuS, _, _ := unstructured.NestedString(usage, "cpu"); cpuS != "" {
					if q, e := resourceParseMilli(cpuS); e == nil {
						cpuMillis += q
					}
				}
				if memS, _, _ := unstructured.NestedString(usage, "memory"); memS != "" {
					if b, e := resourceParseBytes(memS); e == nil {
						memBytes += b
					}
				}
			}
			ns := p.GetNamespace()
			cpuCores := float64(cpuMillis) / 1000.0
			snap.Metrics = append(snap.Metrics, model.Metric{
				Kind: "Pod", Name: p.GetName(), Namespace: &ns, SampleTimestamp: ts,
				WindowSeconds: parseDurationSeconds(windowStr), CpuCores: &cpuCores, MemoryBytes: &memBytes,
			})
		}
		reg.set(sourceStatus("k8s/podmetrics", "ok", now, nil))
	}
	reg.set(sourceStatus("k8s/metrics", "ok", now, nil))
}

// ---- events -------------------------------------------------------------------------

// collectEvents gathers Kubernetes Events into sanitized timeline entries.
// Raw event messages are NOT stored; only bounded allowlisted templates.
func (c *Collector) collectEvents(ctx context.Context, snap *Snapshot, reg *SourceRegistry) {
	now := time.Now()
	list, truncatedEv, err := listWithContinue(ctx, listPage, listCap, func(opts metav1.ListOptions) ([]corev1.Event, string, error) {
		l, e := c.clients.typed.CoreV1().Events("").List(ctx, opts)
		if e != nil {
			return nil, "", e
		}
		return l.Items, l.Continue, nil
	})
	if err != nil {
		reg.set(sourceStatus("k8s/events", "error", now, err))
		snap.setPartial()
		return
	}
	if truncatedEv {
		snap.setPartial()
	}
	for _, e := range list {
		sev := "normal"
		if e.Type == corev1.EventTypeWarning {
			sev = "warning"
		}
		// Identity-aware dedup: same event object (UID) is one row; a recreated
		// object (new UID) must NOT merge with the old.
		dedup := "k8s:" + string(e.UID) + ":" + string(e.InvolvedObject.UID) + ":" + e.Reason
		var st *string
		if !e.LastTimestamp.IsZero() {
			v := e.LastTimestamp.UTC().Format(time.RFC3339)
			st = &v
		} else if !e.EventTime.IsZero() {
			v := e.EventTime.UTC().Format(time.RFC3339)
			st = &v
		}
		objKind := e.InvolvedObject.Kind
		ns := e.Namespace
		name := e.InvolvedObject.Name
		snap.addEvent(model.TimelineEvent{
			ID: dedup, Source: "kubernetes", SourceTime: st, Severity: sev,
			ObjectKind: &objKind, Namespace: &ns, ObjectName: &name,
			ReasonCode: e.Reason, OccurrenceCount: int64(e.Count), Message: "kubernetes event " + e.Reason,
			SourceUID: string(e.UID), SourceResourceVersion: e.ResourceVersion,
		})
	}
	reg.set(sourceStatus("k8s/events", "ok", now, nil))
}

// ---- helpers -------------------------------------------------------------------------

func getString(obj map[string]any, path ...string) string {
	v, _, _ := unstructured.NestedString(obj, path...)
	return v
}

func strPtrOrNil(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}
