// Package store implements the application PostgreSQL persistence layer.
// It connects with verify-full TLS (no non-TLS fallback), owns the versioned
// migration ledger and the two application tables (observation_batches,
// timeline_events). It never touches infrastructure/probe tables and never
// logs DSN, password or credential-bearing errors.
package store

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"strings"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// Store wraps a pgx connection pool scoped to the portal application schema.
type Store struct {
	pool *pgxpool.Pool
}

// New connects to the application database using the fixed DB contract.
// The password is supplied via config (secretKeyRef env) and never logged.
func New(ctx context.Context, cfg *config.Config) (*Store, error) {
	connStr := fmt.Sprintf(
		"host=%s port=%d dbname=%s user=%s sslmode=%s sslrootcert=%s",
		config.DBHost, config.DBPort, config.DBName, config.DBUser, config.DBSSLMode, cfg.DBCACertFile,
	)
	pc, err := pgxpool.ParseConfig(connStr)
	if err != nil {
		return nil, err
	}
	pc.ConnConfig.Password = cfg.DBPassword
	pc.MaxConns = int32(cfg.DBPoolMaxConns)
	pc.MinConns = 0
	pc.ConnConfig.ConnectTimeout = cfg.DBConnectTimeout
	pool, err := pgxpool.NewWithConfig(ctx, pc)
	if err != nil {
		return nil, err
	}
	return &Store{pool: pool}, nil
}

// Close releases the pool.
func (s *Store) Close() { s.pool.Close() }

// Ping verifies connectivity with a bounded timeout.
func (s *Store) Ping(ctx context.Context) error {
	cctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	return s.pool.Ping(cctx)
}

// AdvisoryLockID is the stable application migration lock.
const AdvisoryLockID = 804003001

// Migrate applies the forward-only migration inside a single transaction:
// advisory xact lock, ledger checksum verification, DDL application, then the
// version/checksum ledger write. On repeat with the same checksum it is a no-op;
// on checksum mismatch it returns an error (no DROP, no down migration).
func (s *Store) Migrate(ctx context.Context, version int64, checksum, sourceRevision, ddl string) error {
	cctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	tx, err := s.pool.BeginTx(cctx, pgx.TxOptions{})
	if err != nil {
		return fmt.Errorf("begin migration: %w", err)
	}
	defer tx.Rollback(cctx) //nolint:errcheck

	// lock_timeout + statement_timeout are set per-connection; use local settings.
	if _, err := tx.Exec(cctx, "SET LOCAL lock_timeout = '5s'"); err != nil {
		return fmt.Errorf("set lock_timeout: %w", err)
	}
	if _, err := tx.Exec(cctx, "SET LOCAL statement_timeout = '30s'"); err != nil {
		return fmt.Errorf("set statement_timeout: %w", err)
	}
	if _, err := tx.Exec(cctx, "SELECT pg_advisory_xact_lock($1)", AdvisoryLockID); err != nil {
		return fmt.Errorf("advisory lock: %w", err)
	}

	// Ensure ledger table exists (only the ledger bootstrap may use IF NOT EXISTS).
	if _, err := tx.Exec(cctx, `CREATE TABLE IF NOT EXISTS portal.schema_migrations (
		version bigint PRIMARY KEY CHECK (version > 0),
		checksum text NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
		applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
		source_revision text NOT NULL CHECK (source_revision ~ '^[0-9a-f]{40}$')
	)`); err != nil {
		return fmt.Errorf("bootstrap ledger: %w", err)
	}

	var existing string
	err = tx.QueryRow(cctx,
		"SELECT checksum FROM portal.schema_migrations WHERE version = $1", version,
	).Scan(&existing)
	switch {
	case err == pgx.ErrNoRows:
		// Fresh apply.
		if _, err := tx.Exec(cctx, ddl); err != nil {
			return fmt.Errorf("apply DDL: %w", err)
		}
		if _, err := tx.Exec(cctx,
			"INSERT INTO portal.schema_migrations (version, checksum, source_revision) VALUES ($1,$2,$3)",
			version, checksum, sourceRevision,
		); err != nil {
			return fmt.Errorf("write ledger: %w", err)
		}
	case err != nil:
		return fmt.Errorf("read ledger: %w", err)
	default:
		// Already applied: verify exact checksum; no-op only on exact match.
		if existing != checksum {
			return fmt.Errorf("migration checksum mismatch for version %d: ledger=%s expected=%s", version, existing, checksum)
		}
	}

	return tx.Commit(cctx)
}

// CurrentMigrationVersion returns the applied version and checksum, or zero values.
func (s *Store) CurrentMigrationVersion(ctx context.Context) (int64, string, error) {
	cctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	var v int64
	var c string
	err := s.pool.QueryRow(cctx, "SELECT version, checksum FROM portal.schema_migrations ORDER BY version DESC LIMIT 1").Scan(&v, &c)
	if err == pgx.ErrNoRows {
		return 0, "", nil
	}
	if err != nil {
		return 0, "", err
	}
	return v, c, nil
}

// ChecksumFile returns the hex SHA-256 of the given bytes.
func ChecksumFile(b []byte) string {
	s := sha256.Sum256(b)
	return hex.EncodeToString(s[:])
}

// InsertBatch persists one normalized observation batch (DTO summary only).
func (s *Store) InsertBatch(ctx context.Context, id string, observedAt time.Time, sourceRevision, overallHealth string, partial bool, summary []byte) error {
	cctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	_, err := s.pool.Exec(cctx, `INSERT INTO portal.observation_batches
		(id, observed_at, source_revision, overall_health, partial, summary)
		VALUES ($1,$2,$3,$4,$5,$6)`,
		id, observedAt, sourceRevision, overallHealth, partial, string(summary))
	return err
}

// TimelineEvent is a sanitized event/status entry.
type TimelineEvent struct {
	DedupKey              string
	Source                string
	SourceUID             string
	SourceResourceVersion string
	SourceTime            *time.Time
	Severity              string
	ObjectKind            string
	ObjectNamespace       string
	ObjectName            string
	ReasonCode            string
	Message               string
}

// UpsertEvent inserts or increments a deduplicated timeline event.
func (s *Store) UpsertEvent(ctx context.Context, e TimelineEvent) error {
	cctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	_, err := s.pool.Exec(cctx, `INSERT INTO portal.timeline_events
		(dedup_key, source, source_uid, source_resource_version, source_time, severity,
		 object_kind, object_namespace, object_name, reason_code, occurrence_count, message)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,1,$11)
		ON CONFLICT (dedup_key) DO UPDATE SET
			occurrence_count = timeline_events.occurrence_count + 1,
			ingested_at = CURRENT_TIMESTAMP`,
		e.DedupKey, e.Source, nullStr(e.SourceUID), nullStr(e.SourceResourceVersion), e.SourceTime,
		e.Severity, nullStr(e.ObjectKind), nullStr(e.ObjectNamespace), nullStr(e.ObjectName),
		e.ReasonCode, e.Message)
	return err
}

// EventRow is a persisted timeline event projection.
type EventRow struct {
	ID          string     `json:"id"`
	IngestedAt  time.Time  `json:"ingestedAt"`
	SourceTime  *time.Time `json:"sourceTime"`
	Source      string     `json:"source"`
	Severity    string     `json:"severity"`
	ObjectKind  string     `json:"objectKind"`
	ObjectNS    string     `json:"objectNamespace"`
	ObjectName  string     `json:"objectName"`
	ReasonCode  string     `json:"reasonCode"`
	Occurrences int64      `json:"occurrenceCount"`
	Message     string     `json:"message"`
}

// ListEvents returns recent timeline events, optionally filtered by severity and since.
func (s *Store) ListEvents(ctx context.Context, since *time.Time, severity string, limit int) ([]EventRow, error) {
	cctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	q := `SELECT dedup_key, ingested_at, source_time, source, severity, object_kind, object_namespace, object_name,
		reason_code, occurrence_count, message
		FROM portal.timeline_events`
	var args []any
	var conds []string
	if since != nil {
		conds = append(conds, fmt.Sprintf("ingested_at >= $%d", len(args)+1))
		args = append(args, *since)
	}
	if severity != "" {
		conds = append(conds, fmt.Sprintf("severity = $%d", len(args)+1))
		args = append(args, severity)
	}
	if len(conds) > 0 {
		q += " WHERE " + strings.Join(conds, " AND ")
	}
	q += fmt.Sprintf(" ORDER BY ingested_at DESC, id DESC LIMIT $%d", len(args)+1)
	args = append(args, limit)

	rows, err := s.pool.Query(cctx, q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]EventRow, 0, limit)
	for rows.Next() {
		var r EventRow
		var st *time.Time
		if err := rows.Scan(&r.ID, &r.IngestedAt, &st, &r.Source, &r.Severity, &r.ObjectKind, &r.ObjectNS, &r.ObjectName, &r.ReasonCode, &r.Occurrences, &r.Message); err != nil {
			return nil, err
		}
		r.SourceTime = st
		out = append(out, r)
	}
	return out, rows.Err()
}

// Prune enforces retention + hard caps on the two application tables using a
// PostgreSQL-17-valid CTE (TTL OR excess-over-cap, bounded batch of <=1000 ids).
func (s *Store) Prune(ctx context.Context) error {
	cctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	if err := s.pruneTable(cctx, "portal.observation_batches", "recorded_at", 20000); err != nil {
		return err
	}
	return s.pruneTable(cctx, "portal.timeline_events", "ingested_at", 50000)
}

// pruneTable deletes rows that are expired (TTL 7d) OR beyond the newest `cap`
// rows, in bounded batches of at most 1000 ids per statement. Only these two
// application tables are touched — never system/P8A/P8B objects.
func (s *Store) pruneTable(ctx context.Context, table, timeCol string, cap int) error {
	for i := 0; i < 20; i++ {
		q := fmt.Sprintf(`
			WITH ranked AS (
				SELECT id, row_number() OVER (ORDER BY %s DESC) AS rn,
				       (%s < CURRENT_TIMESTAMP - interval '7 days') AS expired
				FROM %s
			), doomed AS (
				SELECT id FROM ranked WHERE expired OR rn > %d LIMIT 1000
			)
			DELETE FROM %s WHERE id IN (SELECT id FROM doomed)
		`, timeCol, timeCol, table, cap, table)
		tag, err := s.pool.Exec(ctx, q)
		if err != nil {
			return err
		}
		if tag.RowsAffected() < 1000 {
			return nil
		}
	}
	return nil
}

func nullStr(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}
