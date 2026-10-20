// Package collectors polls read-only Kubernetes APIs and the Barman metrics
// service on a fixed interval and publishes an atomic in-memory snapshot of
// sanitized DTOs. Only Get/List (no Watch/mutation). A per-source registry
// records the truthful result of every actual read; errors are never
// overwritten by a later "fresh" mark.
package collectors

import (
	"context"
	"net/http"
	"sync"
	"sync/atomic"
	"time"

	apierrors "k8s.io/apimachinery/pkg/api/errors"
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

// newClients builds in-cluster clients with a transport guard and bounded QPS.
func newClients() (*clients, error) {
	cfg, err := rest.InClusterConfig()
	if err != nil {
		return nil, err
	}
	cfg.QPS = 5
	cfg.Burst = 10
	cfg.WrapTransport = func(rt http.RoundTripper) http.RoundTripper {
		return newGuardTransport(rt, cfg.Host)
	}
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

// SourceRegistry records the truthful result of each actual read.
type SourceRegistry struct {
	mu      sync.Mutex
	sources []model.SourceStatus
}

func (r *SourceRegistry) set(s model.SourceStatus) {
	r.mu.Lock()
	r.sources = append(r.sources, s)
	r.mu.Unlock()
}

func (r *SourceRegistry) list() []model.SourceStatus {
	r.mu.Lock()
	defer r.mu.Unlock()
	out := make([]model.SourceStatus, len(r.sources))
	copy(out, r.sources)
	return out
}

// Snapshot is the atomically published collection result.
type Snapshot struct {
	CollectedAt time.Time
	Nodes       []model.Node
	Workloads   []model.Workload
	Pods        []model.Pod
	Services    []model.Service
	Storage     *model.Storage
	Backups     *model.Backups
	Database    *model.Database
	Metrics     []model.Metric
	Barman      *model.BarmanSample
	Events      []model.TimelineEvent
	Sources     []model.SourceStatus
	Partial     bool
	Warnings    []model.Warning

	mu       sync.Mutex
	partial  bool
	warnings []model.Warning
	events   []model.TimelineEvent
}

// PersistenceState tracks the bounded persistence loop's lag and data loss.
type PersistenceState struct {
	LagSeconds      atomic.Int64
	LastSuccessUnix atomic.Int64
	DataLoss        atomic.Bool
}

func (s *Snapshot) addEvent(e model.TimelineEvent) {
	s.mu.Lock()
	s.events = append(s.events, e)
	s.mu.Unlock()
}

func (s *Snapshot) addWarning(w model.Warning) {
	s.mu.Lock()
	s.warnings = append(s.warnings, w)
	s.mu.Unlock()
}

func (s *Snapshot) setPartial() {
	s.mu.Lock()
	s.partial = true
	s.mu.Unlock()
}

func (s *Snapshot) finalize() {
	s.mu.Lock()
	s.Partial = s.partial
	s.Warnings = append([]model.Warning(nil), s.warnings...)
	s.Events = append([]model.TimelineEvent(nil), s.events...)
	s.mu.Unlock()
}

// Collector runs the polling loop and stores the latest snapshot.
type Collector struct {
	clients    *clients
	interval   time.Duration
	snapshot   atomic.Pointer[Snapshot]
	metricsURL string
	namespace  string
}

// New constructs a Collector.
func New(interval time.Duration, metricsURL, namespace string) (*Collector, error) {
	cl, err := newClients()
	if err != nil {
		return nil, err
	}
	return &Collector{clients: cl, interval: interval, metricsURL: metricsURL, namespace: namespace}, nil
}

// Latest returns the current snapshot (nil before the first collection).
func (c *Collector) Latest() *Snapshot {
	return c.snapshot.Load()
}

// Run starts the collection loop; returns when ctx is cancelled.
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

const maxConcurrent = 4

// collect runs one full collection pass with a hard deadline.
func (c *Collector) collect(ctx context.Context) {
	cctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()

	reg := &SourceRegistry{}
	snap := &Snapshot{CollectedAt: time.Now().UTC()}

	sources := []func(context.Context, *Snapshot, *SourceRegistry){
		c.collectNodes, c.collectWorkloads, c.collectPods, c.collectServices,
		c.collectStorage, c.collectBackups, c.collectDatabase, c.collectMetrics,
		c.collectEvents,
	}

	sem := make(chan struct{}, maxConcurrent)
	var wg sync.WaitGroup
	for _, f := range sources {
		wg.Add(1)
		go func(fn func(context.Context, *Snapshot, *SourceRegistry)) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			fn(cctx, snap, reg)
		}(f)
	}
	wg.Wait()

	c.collectBarmanMetrics(cctx, snap, reg)
	snap.Sources = reg.list()
	snap.finalize()
	c.snapshot.Store(snap)
}

// classifyError maps a Kubernetes/HTTP error to a bounded, fixed errorCode.
func classifyError(err error) string {
	switch {
	case err == nil:
		return ""
	case apierrors.IsForbidden(err):
		return "FORBIDDEN"
	case apierrors.IsNotFound(err):
		return "NOT_FOUND"
	case apierrors.IsTimeout(err):
		return "TIMEOUT"
	case apierrors.IsTooManyRequests(err):
		return "RATE_LIMITED"
	case apierrors.IsServiceUnavailable(err):
		return "CONNECTION_ERROR"
	case isNoKindMatch(err):
		return "UNSUPPORTED"
	default:
		return "CONNECTION_ERROR"
	}
}

func isNoKindMatch(err error) bool {
	_, ok := err.(*noKindMatchError)
	return ok
}

type noKindMatchError struct{ msg string }

func (e *noKindMatchError) Error() string { return e.msg }

// sourceStatus builds a SourceStatus from a read result.
func sourceStatus(id, state string, observedAt time.Time, err error) model.SourceStatus {
	ts := observedAt.UTC().Format(time.RFC3339)
	age := float64(time.Since(observedAt).Seconds())
	if age < 0 {
		age = 0
	}
	var code *string
	if err != nil {
		c := classifyError(err)
		code = &c
	}
	return model.SourceStatus{ID: id, State: state, ObservedAt: &ts, AgeSeconds: &age, ErrorCode: code}
}

func nowPtr() *string {
	ts := time.Now().UTC().Format(time.RFC3339)
	return &ts
}
