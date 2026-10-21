// Package store implements the application PostgreSQL persistence layer.
// It connects with verify-full TLS (no non-TLS fallback), owns the versioned
// migration ledger and the two application tables (observation_batches,
// timeline_events). It never touches infrastructure/probe tables and never
// logs DSN, password or credential-bearing errors.
package store

import (
	"context"
	"crypto/sha256"
	"crypto/tls"
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
	// TLS hardening: explicit minimum TLS 1.2 + SNI; the connection string is
	// fully explicit (host/port/dbname/user/sslmode/sslrootcert), so no PG*
	// ambient environment overrides are read.
	if pc.ConnConfig.TLSConfig != nil {
		pc.ConnConfig.TLSConfig.MinVersion = tls.VersionTLS12
		pc.ConnConfig.TLSConfig.ServerName = config.DBHost
	}
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

// VerifySchema checks the expected application table structure (the columns
// the persistence/read paths depend on). It does not validate ledger contents
// and does not touch infrastructure/probe tables.
func (s *Store) VerifySchema(ctx context.Context) error {
	cctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	checks := []struct{ table, column string }{
		{"portal.observation_batches", "id"},
		{"portal.observation_batches", "observed_at"},
		{"portal.observation_batches", "recorded_at"},
		{"portal.observation_batches", "source_revision"},
		{"portal.observation_batches", "overall_health"},
		{"portal.observation_batches", "partial"},
		{"portal.observation_batches", "summary"},
		{"portal.timeline_events", "id"},
		{"portal.timeline_events", "dedup_key"},
		{"portal.timeline_events", "source"},
		{"portal.timeline_events", "source_uid"},
		{"portal.timeline_events", "source_resource_version"},
		{"portal.timeline_events", "source_time"},
		{"portal.timeline_events", "ingested_at"},
		{"portal.timeline_events", "severity"},
		{"portal.timeline_events", "object_kind"},
		{"portal.timeline_events", "object_namespace"},
		{"portal.timeline_events", "object_name"},
		{"portal.timeline_events", "reason_code"},
		{"portal.timeline_events", "occurrence_count"},
		{"portal.timeline_events", "message"},
	}
	for _, c := range checks {
		q := fmt.Sprintf("SELECT %s FROM %s LIMIT 0", c.column, c.table)
		if _, err := s.pool.Exec(cctx, q); err != nil {
			return fmt.Errorf("schema structure %s.%s: %w", c.table, c.column, err)
		}
	}
	// Type checks: SELECT col LIMIT 0 does not catch an incompatible column type
	// (e.g. int8 vs text). Verify the expected information_schema data_type.
	typeChecks := []struct{ column, wantType string }{
		{"id", "bigint"},
		{"dedup_key", "character varying"},
		{"source_time", "timestamp with time zone"},
		{"ingested_at", "timestamp with time zone"},
		{"occurrence_count", "bigint"},
	}
	for _, tc := range typeChecks {
		var dt string
		if err := s.pool.QueryRow(cctx,
			`SELECT data_type FROM information_schema.columns
			 WHERE table_schema='portal' AND table_name='timeline_events' AND column_name=$1`,
			tc.column).Scan(&dt); err != nil {
			return fmt.Errorf("schema type timeline_events.%s: %w", tc.column, err)
		}
		if dt != tc.wantType {
			return fmt.Errorf("schema type timeline_events.%s: want %s got %s", tc.column, tc.wantType, dt)
		}
	}
	// Constraint checks: dedup_key must have a UNIQUE constraint (identity for
	// the upsert ON CONFLICT (dedup_key)).
	var n int
	if err := s.pool.QueryRow(cctx,
		`SELECT count(*) FROM information_schema.table_constraints tc
		 JOIN information_schema.key_column_usage kcu
		   ON tc.constraint_name = kcu.constraint_name AND tc.constraint_schema = kcu.constraint_schema
		 WHERE tc.constraint_schema='portal' AND tc.table_name='timeline_events'
		   AND tc.constraint_type='UNIQUE' AND kcu.column_name='dedup_key'`).Scan(&n); err != nil {
		return fmt.Errorf("schema constraint check: %w", err)
	}
	if n == 0 {
		return fmt.Errorf("schema constraint: timeline_events.dedup_key UNIQUE missing")
	}
	return nil
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
		VALUES ($1,$2,$3,$4,$5,$6)
		ON CONFLICT (id) DO NOTHING`,
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
	Occurrences           int64
	Message               string
}

// UpsertEvent inserts or idempotently refreshes a deduplicated timeline event.
// The occurrence count reflects the source count (never incremented blindly),
// so a repeated poll of an unchanged event does not inflate the count.
func (s *Store) UpsertEvent(ctx context.Context, e TimelineEvent) error {
	cctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	occ := e.Occurrences
	if occ < 1 {
		occ = 1
	}
	_, err := s.pool.Exec(cctx, `INSERT INTO portal.timeline_events
		(dedup_key, source, source_uid, source_resource_version, source_time, severity,
		 object_kind, object_namespace, object_name, reason_code, occurrence_count, message)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
		ON CONFLICT (dedup_key) DO UPDATE SET
			occurrence_count = EXCLUDED.occurrence_count,
			source_uid = EXCLUDED.source_uid,
			source_resource_version = EXCLUDED.source_resource_version,
			source_time = EXCLUDED.source_time,
			severity = EXCLUDED.severity,
			message = EXCLUDED.message,
			ingested_at = CURRENT_TIMESTAMP`,
		e.DedupKey, e.Source, nullStr(e.SourceUID), nullStr(e.SourceResourceVersion), e.SourceTime,
		e.Severity, nullStr(e.ObjectKind), nullStr(e.ObjectNamespace), nullStr(e.ObjectName),
		e.ReasonCode, occ, e.Message)
	return err
}

// EventRow is a persisted timeline event projection. Seq is the stable
// bigserial identity used for keyset pagination (id in the table).
type EventRow struct {
	Seq         int64      `json:"-"`
	ID          string     `json:"id"`
	IngestedAt  time.Time  `json:"ingestedAt"`
	SourceTime  *time.Time `json:"sourceTime"`
	Source      string     `json:"source"`
	Severity    string     `json:"severity"`
	ObjectKind  *string    `json:"objectKind"`
	ObjectNS    *string    `json:"objectNamespace"`
	ObjectName  *string    `json:"objectName"`
	ReasonCode  string     `json:"reasonCode"`
	Occurrences int64      `json:"occurrenceCount"`
	Message     string     `json:"message"`
}

// ListEvents returns recent timeline events filtered by since/severity/namespace,
// paginated by a STABLE keyset (id < afterID, ordered id DESC). The bigserial id
// never changes on upsert, so concurrent insert/update/prune cannot shift pages
// (unlike ORDER BY ingested_at + OFFSET). afterID<=0 means "from the newest".
func (s *Store) ListEvents(ctx context.Context, since *time.Time, severity, namespace string, limit int, afterID int64) ([]EventRow, error) {
	cctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	q := `SELECT id, dedup_key, ingested_at, source_time, source, severity, object_kind, object_namespace, object_name,
		reason_code, occurrence_count, message
		FROM portal.timeline_events`
	var args []any
	var conds []string
	if since != nil {
		// "since" filters by source_time (when the event occurred), matching the
		// in-memory fallback semantics. NULL source_time is excluded (consistent
		// with the fallback, which drops null-SourceTime events under since).
		conds = append(conds, fmt.Sprintf("source_time >= $%d", len(args)+1))
		args = append(args, *since)
	}
	if severity != "" {
		conds = append(conds, fmt.Sprintf("severity = $%d", len(args)+1))
		args = append(args, severity)
	}
	if namespace != "" {
		conds = append(conds, fmt.Sprintf("object_namespace = $%d", len(args)+1))
		args = append(args, namespace)
	}
	if afterID > 0 {
		conds = append(conds, fmt.Sprintf("id < $%d", len(args)+1))
		args = append(args, afterID)
	}
	if len(conds) > 0 {
		q += " WHERE " + strings.Join(conds, " AND ")
	}
	q += fmt.Sprintf(" ORDER BY id DESC LIMIT $%d", len(args)+1)
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
		var objKind, objNS, objName *string
		if err := rows.Scan(&r.Seq, &r.ID, &r.IngestedAt, &st, &r.Source, &r.Severity, &objKind, &objNS, &objName, &r.ReasonCode, &r.Occurrences, &r.Message); err != nil {
			return nil, err
		}
		r.SourceTime = st
		r.ObjectKind = objKind
		r.ObjectNS = objNS
		r.ObjectName = objName
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
