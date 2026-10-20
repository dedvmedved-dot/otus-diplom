//go:build integration

// Package store integration tests run against an isolated PostgreSQL 17
// (CI service container postgres:17). They are NOT part of `go test ./...`;
// run with: TEST_DATABASE_URL=postgres://... go test -tags integration ./internal/store/
package store

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

func integrationPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	url := os.Getenv("TEST_DATABASE_URL")
	if url == "" {
		t.Skip("TEST_DATABASE_URL not set; run in CI with postgres:17")
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, url)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	t.Cleanup(pool.Close)
	if _, err := pool.Exec(ctx, `CREATE SCHEMA IF NOT EXISTS portal`); err != nil {
		t.Fatalf("create schema: %v", err)
	}
	return pool
}

func migrate(t *testing.T, pool *pgxpool.Pool, version int64, checksum, rev, ddl string) {
	t.Helper()
	ctx := context.Background()
	tx, err := pool.Begin(ctx)
	if err != nil {
		t.Fatalf("begin: %v", err)
	}
	defer tx.Rollback(ctx) //nolint:errcheck
	if _, err := tx.Exec(ctx, `SELECT pg_advisory_xact_lock($1)`, AdvisoryLockID); err != nil {
		t.Fatalf("lock: %v", err)
	}
	if _, err := tx.Exec(ctx, `CREATE TABLE IF NOT EXISTS portal.schema_migrations (
		version bigint PRIMARY KEY CHECK (version > 0),
		checksum text NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
		applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
		source_revision text NOT NULL CHECK (source_revision ~ '^[0-9a-f]{40}$')
	)`); err != nil {
		t.Fatalf("ledger: %v", err)
	}
	if _, err := tx.Exec(ctx, ddl); err != nil {
		t.Fatalf("ddl: %v", err)
	}
	if _, err := tx.Exec(ctx, `INSERT INTO portal.schema_migrations (version, checksum, source_revision) VALUES ($1,$2,$3)`, version, checksum, rev); err != nil {
		t.Fatalf("ledger write: %v", err)
	}
	if err := tx.Commit(ctx); err != nil {
		t.Fatalf("commit: %v", err)
	}
}

const ddl = `
CREATE TABLE portal.observation_batches (
    id uuid PRIMARY KEY,
    observed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_revision text NOT NULL CHECK (source_revision ~ '^[0-9a-f]{40}$'),
    overall_health text NOT NULL CHECK (overall_health IN ('healthy','warning','critical','unknown')),
    partial boolean NOT NULL,
    summary jsonb NOT NULL CHECK (jsonb_typeof(summary)='object' AND octet_length(summary::text) <= 65536)
);
CREATE TABLE portal.timeline_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dedup_key varchar(180) NOT NULL UNIQUE,
    source varchar(32) NOT NULL CHECK (source IN ('kubernetes','portal-status')),
    source_uid varchar(80), source_resource_version varchar(80), source_time timestamptz,
    ingested_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    severity varchar(16) NOT NULL CHECK (severity IN ('normal','warning','critical')),
    object_kind varchar(80), object_namespace varchar(63), object_name varchar(253),
    reason_code varchar(80) NOT NULL,
    occurrence_count bigint NOT NULL DEFAULT 1 CHECK (occurrence_count > 0),
    message varchar(1024) NOT NULL
);
`

func TestIntegrationEventDedupIdempotent(t *testing.T) {
	pool := integrationPool(t)
	ctx := context.Background()
	migrate(t, pool, 1, checksumOf(ddl), "a000000000000000000000000000000000000000", ddl)
	s := &Store{pool: pool}

	e := TimelineEvent{DedupKey: "k8s:uid-1:obj-1:reason", Source: "kubernetes", Severity: "warning",
		ReasonCode: "reason", Occurrences: 3, Message: "kubernetes event reason"}
	if err := s.UpsertEvent(ctx, e); err != nil {
		t.Fatalf("upsert: %v", err)
	}
	// Same event, unchanged: occurrence_count must NOT increment (idempotent).
	if err := s.UpsertEvent(ctx, e); err != nil {
		t.Fatalf("upsert2: %v", err)
	}
	rows, err := s.ListEvents(ctx, nil, "", "", 10, 0)
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(rows) != 1 || rows[0].Occurrences != 3 {
		t.Fatalf("expected one event with count 3, got %d rows count %d", len(rows), rows[0].Occurrences)
	}
	// Recreated object (new UID) must NOT merge.
	e2 := TimelineEvent{DedupKey: "k8s:uid-2:obj-1:reason", Source: "kubernetes", Severity: "warning",
		ReasonCode: "reason", Occurrences: 1, Message: "kubernetes event reason"}
	if err := s.UpsertEvent(ctx, e2); err != nil {
		t.Fatalf("upsert3: %v", err)
	}
	rows, _ = s.ListEvents(ctx, nil, "", "", 10, 0)
	if len(rows) != 2 {
		t.Fatalf("expected two distinct events, got %d", len(rows))
	}
}

func TestIntegrationPruneTTLAndCap(t *testing.T) {
	pool := integrationPool(t)
	ctx := context.Background()
	migrate(t, pool, 1, checksumOf(ddl), "a000000000000000000000000000000000000000", ddl)
	s := &Store{pool: pool}

	// Insert a batch far in the past (TTL expired) and a recent one.
	oldID := "00000000-0000-0000-0000-000000000001"
	if _, err := pool.Exec(ctx, `INSERT INTO portal.observation_batches (id, observed_at, source_revision, overall_health, partial, summary)
		VALUES ($1, now() - interval '8 days', 'a000000000000000000000000000000000000000', 'healthy', false, '{}')`, oldID); err != nil {
		t.Fatalf("insert old: %v", err)
	}
	newID := "00000000-0000-0000-0000-000000000002"
	if _, err := pool.Exec(ctx, `INSERT INTO portal.observation_batches (id, observed_at, source_revision, overall_health, partial, summary)
		VALUES ($1, now(), 'a000000000000000000000000000000000000000', 'healthy', false, '{}')`, newID); err != nil {
		t.Fatalf("insert new: %v", err)
	}
	if err := s.Prune(ctx); err != nil {
		t.Fatalf("prune: %v", err)
	}
	var cnt int
	if err := pool.QueryRow(ctx, `SELECT count(*) FROM portal.observation_batches`).Scan(&cnt); err != nil {
		t.Fatalf("count: %v", err)
	}
	if cnt != 1 {
		t.Fatalf("expected 1 batch after TTL prune, got %d", cnt)
	}
}

func TestIntegrationMigrationNoopAndMismatch(t *testing.T) {
	pool := integrationPool(t)
	ctx := context.Background()
	checksum := checksumOf(ddl)
	rev := "a000000000000000000000000000000000000000"
	s := &Store{pool: pool}
	if err := s.Migrate(ctx, 1, checksum, rev, ddl); err != nil {
		t.Fatalf("migrate: %v", err)
	}
	// Repeat with same checksum -> no-op (idempotent).
	if err := s.Migrate(ctx, 1, checksum, rev, ddl); err != nil {
		t.Fatalf("repeat migrate: %v", err)
	}
	// Mismatch -> error (no silent drift).
	if err := s.Migrate(ctx, 1, checksumOf("different"), rev, ddl); err == nil {
		t.Fatal("expected checksum mismatch error")
	}
}

func checksumOf(s string) string {
	return ChecksumFile([]byte(s))
}

var _ = time.Second
