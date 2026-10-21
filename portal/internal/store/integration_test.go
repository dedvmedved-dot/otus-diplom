//go:build integration

// Package store integration tests run against an isolated, disposable
// PostgreSQL 17 (local cluster or CI postgres:17 service). They are NOT part of
// `go test ./...`; run with:
//   TEST_DATABASE_URL=postgres://... go test -tags integration ./internal/store/
// The suite FAILS (not skips) if TEST_DATABASE_URL is unset.
package store

import (
	"context"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/migrations"
	"github.com/jackc/pgx/v5/pgxpool"
)

const sourceRev = "a000000000000000000000000000000000000000"

func integrationPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	url := os.Getenv("TEST_DATABASE_URL")
	if url == "" {
		t.Fatal("TEST_DATABASE_URL is unset; integration tests require an isolated PostgreSQL 17")
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, url)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	t.Cleanup(pool.Close)
	return pool
}

// freshSchema drops and recreates the application schema for full isolation.
func freshSchema(t *testing.T) (*pgxpool.Pool, *Store) {
	t.Helper()
	pool := integrationPool(t)
	ctx := context.Background()
	if _, err := pool.Exec(ctx, `DROP SCHEMA IF EXISTS portal CASCADE`); err != nil {
		t.Fatalf("drop schema: %v", err)
	}
	if _, err := pool.Exec(ctx, `CREATE SCHEMA portal`); err != nil {
		t.Fatalf("create schema: %v", err)
	}
	s := &Store{pool: pool}
	// Apply the ACTUAL embedded migration (not a duplicate DDL string).
	if err := s.Migrate(ctx, migrations.Version0001, migrations.Checksum0001(), sourceRev, migrations.SQL0001); err != nil {
		t.Fatalf("migrate: %v", err)
	}
	return pool, s
}

func batchCount(t *testing.T, pool *pgxpool.Pool) int {
	t.Helper()
	var n int
	if err := pool.QueryRow(context.Background(), `SELECT count(*) FROM portal.observation_batches`).Scan(&n); err != nil {
		t.Fatalf("count batches: %v", err)
	}
	return n
}

func TestIntegrationInsertBatchIdempotent(t *testing.T) {
	pool, s := freshSchema(t)
	ctx := context.Background()
	id := "00000000-0000-0000-0000-000000000001"
	if err := s.InsertBatch(ctx, id, time.Now(), sourceRev, "healthy", false, []byte(`{"partial":false}`)); err != nil {
		t.Fatalf("insert: %v", err)
	}
	// Same id -> ON CONFLICT DO NOTHING -> still one batch.
	if err := s.InsertBatch(ctx, id, time.Now(), sourceRev, "healthy", false, []byte(`{"partial":false}`)); err != nil {
		t.Fatalf("insert2: %v", err)
	}
	if batchCount(t, pool) != 1 {
		t.Fatalf("expected 1 batch (idempotent), got %d", batchCount(t, pool))
	}
}

func TestIntegrationEventDedupAndRecreate(t *testing.T) {
	_, s := freshSchema(t)
	ctx := context.Background()

	// NULL object fields must round-trip as nil (no scan into string).
	e := TimelineEvent{DedupKey: "k8s:uid-1:obj-1:reason", Source: "kubernetes", Severity: "warning",
		ReasonCode: "reason", Occurrences: 3, Message: "event"}
	if err := s.UpsertEvent(ctx, e); err != nil {
		t.Fatalf("upsert: %v", err)
	}
	// Same event unchanged -> count NOT incremented (idempotent).
	if err := s.UpsertEvent(ctx, e); err != nil {
		t.Fatalf("upsert2: %v", err)
	}
	rows, err := s.ListEvents(ctx, nil, "", "", 10, 0)
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(rows) != 1 || rows[0].Occurrences != 3 {
		t.Fatalf("expected 1 row count 3, got %d rows count %d", len(rows), rows[0].Occurrences)
	}
	if rows[0].ObjectKind != nil || rows[0].ObjectNS != nil || rows[0].ObjectName != nil {
		t.Fatal("NULL object fields must read back as nil")
	}
	// Increased source count -> occurrence_count updates.
	e.Occurrences = 5
	if err := s.UpsertEvent(ctx, e); err != nil {
		t.Fatalf("upsert3: %v", err)
	}
	rows, _ = s.ListEvents(ctx, nil, "", "", 10, 0)
	if rows[0].Occurrences != 5 {
		t.Fatalf("expected count 5 after increase, got %d", rows[0].Occurrences)
	}
	// Recreated object (new UID) -> distinct row, NOT merged.
	e2 := TimelineEvent{DedupKey: "k8s:uid-2:obj-1:reason", Source: "kubernetes", Severity: "warning",
		ReasonCode: "reason", Occurrences: 1, Message: "event"}
	if err := s.UpsertEvent(ctx, e2); err != nil {
		t.Fatalf("upsert4: %v", err)
	}
	rows, _ = s.ListEvents(ctx, nil, "", "", 10, 0)
	if len(rows) != 2 {
		t.Fatalf("expected 2 distinct events, got %d", len(rows))
	}
}

func TestIntegrationPruneTTL(t *testing.T) {
	pool, s := freshSchema(t)
	ctx := context.Background()
	// Expired by recorded_at (>7d), NOT observed_at.
	if _, err := pool.Exec(ctx, `INSERT INTO portal.observation_batches (id, observed_at, recorded_at, source_revision, overall_health, partial, summary)
		VALUES (gen_random_uuid(), now(), now() - interval '8 days', $1, 'healthy', false, '{}')`, sourceRev); err != nil {
		t.Fatalf("insert old: %v", err)
	}
	// Recent.
	if _, err := pool.Exec(ctx, `INSERT INTO portal.observation_batches (id, observed_at, recorded_at, source_revision, overall_health, partial, summary)
		VALUES (gen_random_uuid(), now(), now(), $1, 'healthy', false, '{}')`, sourceRev); err != nil {
		t.Fatalf("insert new: %v", err)
	}
	if err := s.Prune(ctx); err != nil {
		t.Fatalf("prune: %v", err)
	}
	if n := batchCount(t, pool); n != 1 {
		t.Fatalf("expected 1 batch after TTL prune, got %d", n)
	}
}

func TestIntegrationPruneCap(t *testing.T) {
	pool, s := freshSchema(t)
	ctx := context.Background()
	// Insert 20005 recent batches (over the 20000 cap) in one statement.
	if _, err := pool.Exec(ctx, `INSERT INTO portal.observation_batches (id, observed_at, recorded_at, source_revision, overall_health, partial, summary)
		SELECT gen_random_uuid(), now(), now(), $1, 'healthy', false, '{}' FROM generate_series(1, 20005)`, sourceRev); err != nil {
		t.Fatalf("insert cap rows: %v", err)
	}
	if err := s.Prune(ctx); err != nil {
		t.Fatalf("prune: %v", err)
	}
	if n := batchCount(t, pool); n > 20000 {
		t.Fatalf("expected <=20000 after cap prune, got %d", n)
	}
}

func TestIntegrationMigrationNoopAndMismatch(t *testing.T) {
	_, s := freshSchema(t)
	ctx := context.Background()
	// Repeat with same checksum -> no-op.
	if err := s.Migrate(ctx, migrations.Version0001, migrations.Checksum0001(), sourceRev, migrations.SQL0001); err != nil {
		t.Fatalf("repeat migrate: %v", err)
	}
	// Different checksum -> error (no silent drift).
	if err := s.Migrate(ctx, migrations.Version0001, strings.Repeat("b", 64), sourceRev, migrations.SQL0001); err == nil {
		t.Fatal("expected checksum mismatch error")
	}
}

func TestIntegrationLedgerDrift(t *testing.T) {
	pool, s := freshSchema(t)
	ctx := context.Background()
	// Corrupt ledger checksum -> Migrate must detect drift on next attempt.
	if _, err := pool.Exec(ctx, `UPDATE portal.schema_migrations SET checksum = $1`, strings.Repeat("c", 64)); err != nil {
		t.Fatalf("corrupt ledger: %v", err)
	}
	if err := s.Migrate(ctx, migrations.Version0001, migrations.Checksum0001(), sourceRev, migrations.SQL0001); err == nil {
		t.Fatal("expected drift error on corrupted ledger checksum")
	}
}

func TestIntegrationVerifySchemaNegative(t *testing.T) {
	pool, s := freshSchema(t)
	ctx := context.Background()
	// Drop an application table while the ledger stays correct: readiness
	// (VerifySchema) must fail even though the ledger version matches.
	if _, err := pool.Exec(ctx, `DROP TABLE portal.timeline_events`); err != nil {
		t.Fatalf("drop table: %v", err)
	}
	ver, checksum, err := s.CurrentMigrationVersion(ctx)
	if err != nil || ver != migrations.Version0001 || checksum == "" {
		t.Fatalf("ledger should be intact: ver=%d checksum=%q err=%v", ver, checksum, err)
	}
	if err := s.VerifySchema(ctx); err == nil {
		t.Fatal("expected VerifySchema to fail with missing timeline_events table")
	}
}
