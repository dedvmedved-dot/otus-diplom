// Command portal is the read-only PAK Portal operator console (single monolith:
// UI + API + collectors + PostgreSQL persistence). Run without arguments to
// serve; run with the "migrate" argument to apply the versioned schema.
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync/atomic"
	"syscall"

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

// runMigrate applies the versioned forward-only migration and exits.
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

// runServer starts the collectors, HTTP server and management probes.
func runServer(cfg *config.Config) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	st, err := store.New(ctx, cfg)
	if err != nil {
		log.Fatalf("db connect: %v", err)
	}
	defer st.Close()

	verifier, err := auth.NewVerifier(cfg.AuthUsername, cfg.AuthVerifierFile)
	if err != nil {
		log.Fatalf("auth verifier: %v", err)
	}

	col, err := collectors.New(cfg.CollectInterval, cfg.MetricsServiceURL)
	if err != nil {
		log.Fatalf("collector: %v", err)
	}
	go col.Run(ctx)

	srv := httpapi.New(col, st, verifier, cfg)

	var migrationOK atomic.Bool
	ver, _, err := st.CurrentMigrationVersion(ctx)
	if err == nil && ver >= migrations.Version0001 {
		migrationOK.Store(true)
	} else {
		log.Printf("warning: migration version not yet validated (err=%v, version=%d)", err, ver)
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
		log.Printf("management probes on %s", cfg.MgmtAddr)
		if err := http.ListenAndServe(cfg.MgmtAddr, mgmt); err != nil {
			log.Fatalf("mgmt server: %v", err)
		}
	}()

	go func() {
		log.Printf("serving on %s (revision %s)", cfg.ServerAddr, sourceRevision)
		if err := http.ListenAndServe(cfg.ServerAddr, srv.Handler()); err != nil {
			log.Fatalf("http server: %v", err)
		}
	}()

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Printf("shutting down")
	cancel()
}
