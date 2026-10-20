// Package collectors polls read-only Kubernetes APIs and the Barman metrics
// service on a fixed interval and publishes an atomic in-memory snapshot of
// sanitized DTOs. It uses only Get/List (no Watch, no mutation). Transport
// guard: fixed GVRs, no user-controlled paths, no redirects.
package collectors

import (
	"context"
	"sync"
	"sync/atomic"
	"time"

	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
)

// clients holds the typed and dynamic Kubernetes clients.
type clients struct {
	typed   kubernetes.Interface
	dynamic dynamic.Interface
}

// newClients builds in-cluster clients with bounded QPS/burst.
func newClients() (*clients, error) {
	cfg, err := rest.InClusterConfig()
	if err != nil {
		return nil, err
	}
	cfg.QPS = 5
	cfg.Burst = 10
	typed, err := kubernetes.NewForConfig(cfg)
	if err != nil {
		return nil, err
	}
	dyn, err := dynamic.NewForConfig(cfg)
	if err != nil {
		return nil, err
	}
	return &clients{typed: typed, dynamic: dyn}, nil
}

// Snapshot is the atomically published collection result.
type Snapshot struct {
	CollectedAt   time.Time
	Nodes         []model.NodeInfo
	Workloads     []model.WorkloadInfo
	Pods          []model.PodInfo
	Services      []model.ServiceInfo
	Storage       []model.StorageInfo
	Backups       []model.BackupInfo
	Database      *model.DatabaseInfo
	Metrics       []model.MetricInfo
	BarmanMetrics map[string]string
	Sources       []model.SourceStatus
	OverallHealth string
	Partial       bool
	Warnings      []string

	mu sync.Mutex // guards Sources + Warnings
}

func (s *Snapshot) addSource(st model.SourceStatus) {
	s.mu.Lock()
	s.Sources = append(s.Sources, st)
	s.mu.Unlock()
}

func (s *Snapshot) addWarning(w string) {
	s.mu.Lock()
	s.Warnings = append(s.Warnings, w)
	s.mu.Unlock()
}

// Collector runs the polling loop and stores the latest snapshot.
type Collector struct {
	clients    *clients
	interval   time.Duration
	snapshot   atomic.Pointer[Snapshot]
	metricsURL string
}

// New constructs a Collector.
func New(interval time.Duration, metricsURL string) (*Collector, error) {
	cl, err := newClients()
	if err != nil {
		return nil, err
	}
	return &Collector{clients: cl, interval: interval, metricsURL: metricsURL}, nil
}

// Latest returns the current snapshot (may be nil before the first collection).
func (c *Collector) Latest() *Snapshot {
	return c.snapshot.Load()
}

// Run starts the collection loop; it returns when ctx is cancelled.
func (c *Collector) Run(ctx context.Context) {
	c.collect(ctx)
	ticker := time.NewTicker(c.interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			c.collect(ctx)
		}
	}
}

// maxConcurrent limits simultaneous source reads (fixed requirement).
const maxConcurrent = 4

// collect runs one full collection pass with a hard deadline.
func (c *Collector) collect(ctx context.Context) {
	cctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()

	snap := &Snapshot{
		CollectedAt:   time.Now().UTC(),
		BarmanMetrics: map[string]string{},
	}

	sources := []func(context.Context, *Snapshot){
		c.collectNodes, c.collectWorkloads, c.collectPods, c.collectServices,
		c.collectStorage, c.collectBackups, c.collectDatabase, c.collectMetrics,
	}

	sem := make(chan struct{}, maxConcurrent)
	var wg sync.WaitGroup
	for _, f := range sources {
		wg.Add(1)
		go func(fn func(context.Context, *Snapshot)) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			fn(cctx, snap)
		}(f)
	}
	wg.Wait()

	c.collectBarmanMetrics(cctx, snap)
	c.computeHealth(snap)
	c.snapshot.Store(snap)
}
