// Command portal is the read-only PAK Portal operator console (single monolith:
// UI + API + collectors + PostgreSQL persistence). Run without arguments to
// serve; run with the "migrate" argument to apply the versioned schema.
package main

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/auth"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/httpapi"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/store"
	"github.com/dedvmedved-dot/otus-diplom/portal/migrations"
)

var (
	sourceRevision = "unknown"
	buildTime      = "unknown"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config: %v", err)
	}
	cfg.SourceRevision = sourceRevision
	cfg.BuildTime = buildTime

	if len(os.Args) > 1 && os.Args[1] == "migrate" {
		runMigrate(cfg)
		return
	}
	runServer(cfg)
}

func runMigrate(cfg *config.Config) {
	ctx := context.Background()
	st, err := store.New(ctx, cfg)
	if err != nil {
		log.Fatalf("db connect: %v", err)
	}
	defer st.Close()
	if err := st.Migrate(ctx, migrations.Version0001, migrations.Checksum0001(), sourceRevision, migrations.SQL0001); err != nil {
		log.Fatalf("migrate: %v", err)
	}
	log.Printf("migration version %d applied (checksum %s)", migrations.Version0001, migrations.Checksum0001()[:12])
}

func runServer(cfg *config.Config) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	st, err := store.New(ctx, cfg)
	if err != nil {
		log.Fatalf("db connect: %v", err)
	}
	defer st.Close()

	verifier, err := auth.NewVerifier(cfg.AuthUsername, cfg.AuthVerifier)
	if err != nil {
		log.Fatalf("auth verifier: %v", err)
	}

	col, err := collectors.New(cfg.CollectInterval, cfg.MetricsServiceURL, cfg.Namespace)
	if err != nil {
		log.Fatalf("collector: %v", err)
	}
	go col.Run(ctx)

	ps := &collectors.PersistenceState{}
	go runPersistence(ctx, st, col, cfg, ps)

	srv := httpapi.New(col, st, verifier, cfg, ps)

	// Readiness requires exact migration version + checksum (not just >=1).
	var migrationOK atomic.Bool
	ver, checksum, err := st.CurrentMigrationVersion(ctx)
	if err == nil && ver == migrations.Version0001 && checksum == migrations.Checksum0001() {
		migrationOK.Store(true)
	} else {
		log.Printf("warning: migration not validated (version=%d err=%v)", ver, err)
	}

	ready := func(w http.ResponseWriter, _ *http.Request) {
		if !migrationOK.Load() {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		if col.Latest() == nil {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
	}

	mgmt := http.NewServeMux()
	mgmt.HandleFunc("/livez", func(w http.ResponseWriter, _ *http.Request) { w.WriteHeader(http.StatusOK) })
	mgmt.HandleFunc("/readyz", ready)
	mgmt.HandleFunc("/startupz", ready)
	go func() {
		ms := &http.Server{
			Addr: cfg.MgmtAddr, Handler: mgmt,
			ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second,
			WriteTimeout: 10 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 1 << 20,
		}
		log.Printf("management probes on %s", cfg.MgmtAddr)
		if err := ms.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("mgmt server: %v", err)
		}
	}()

	go func() {
		hs := &http.Server{
			Addr: cfg.ServerAddr, Handler: srv.Handler(),
			ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second,
			WriteTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 1 << 20,
		}
		log.Printf("serving on %s (revision %s)", cfg.ServerAddr, sourceRevision)
		if err := hs.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("http server: %v", err)
		}
	}()

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Printf("shutting down")
	cancel()
}

// runPersistence runs the bounded background persistence loop (batch + events +
// prune). It never blocks the UI/API; on failure it marks data loss.
func runPersistence(ctx context.Context, st *store.Store, col *collectors.Collector, cfg *config.Config, ps *collectors.PersistenceState) {
	ticker := time.NewTicker(cfg.CollectInterval)
	defer ticker.Stop()
	var pruneCounter int
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			persistOnce(ctx, st, col, cfg, ps)
			pruneCounter++
			if pruneCounter%60 == 0 {
				_ = st.Prune(ctx)
			}
		}
	}
}

func persistOnce(ctx context.Context, st *store.Store, col *collectors.Collector, cfg *config.Config, ps *collectors.PersistenceState) {
	snap := col.Latest()
	if snap == nil {
		return
	}
	summary := buildSummaryJSON(snap)
	id := newUUID()
	if err := st.InsertBatch(ctx, id, snap.CollectedAt, cfg.SourceRevision, "unknown", snap.Partial, summary); err != nil {
		ps.DataLoss.Store(true)
		ps.LagSeconds.Add(1)
		return
	}
	writeFailed := false
	for _, e := range snap.Events {
		se := store.TimelineEvent{
			DedupKey: e.ID, Source: e.Source, Severity: e.Severity, ReasonCode: e.ReasonCode,
			Occurrences: e.OccurrenceCount, Message: e.Message,
		}
		if e.SourceTime != nil {
			if t, err := time.Parse(time.RFC3339, *e.SourceTime); err == nil {
				se.SourceTime = &t
			}
		}
		if e.ObjectKind != nil {
			se.ObjectKind = *e.ObjectKind
		}
		if e.Namespace != nil {
			se.ObjectNamespace = *e.Namespace
		}
		if e.ObjectName != nil {
			se.ObjectName = *e.ObjectName
		}
		if err := st.UpsertEvent(ctx, se); err != nil {
			writeFailed = true
		}
	}
	if writeFailed {
		ps.DataLoss.Store(true)
		ps.LagSeconds.Add(1)
		return
	}
	ps.LagSeconds.Store(0)
}

func buildSummaryJSON(snap *collectors.Snapshot) []byte {
	s := map[string]any{
		"nodes":     len(snap.Nodes),
		"workloads": len(snap.Workloads),
		"pods":      len(snap.Pods),
		"services":  len(snap.Services),
		"metrics":   len(snap.Metrics),
		"partial":   snap.Partial,
	}
	b, _ := json.Marshal(s)
	return b
}

func newUUID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
