-- P8C-R1 application schema migration (version 1).
-- Runner connects as portal_app to portal-db-rw.portal.svc with verify-full.
-- Runner owns BEGIN/COMMIT, advisory lock 804003001, timeouts and checksum ledger.
-- Schema portal must already exist. No infrastructure/probe tables are touched.
-- Bootstrap ledger below only after exact existing-object inspection.
CREATE TABLE IF NOT EXISTS portal.schema_migrations (
    version bigint PRIMARY KEY CHECK (version > 0),
    checksum text NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
    applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_revision text NOT NULL CHECK (source_revision ~ '^[0-9a-f]{40}$')
);

CREATE TABLE portal.observation_batches (
    id uuid PRIMARY KEY,
    observed_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_revision text NOT NULL CHECK (source_revision ~ '^[0-9a-f]{40}$'),
    overall_health text NOT NULL CHECK (overall_health IN ('healthy','warning','critical','unknown')),
    partial boolean NOT NULL,
    summary jsonb NOT NULL CHECK (
        jsonb_typeof(summary) = 'object' AND octet_length(summary::text) <= 65536
    )
);
CREATE INDEX observation_batches_observed_at_idx
    ON portal.observation_batches (observed_at DESC, id);

CREATE TABLE portal.timeline_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dedup_key varchar(180) NOT NULL UNIQUE,
    source varchar(32) NOT NULL CHECK (source IN ('kubernetes','portal-status')),
    source_uid varchar(80),
    source_resource_version varchar(80),
    source_time timestamptz,
    ingested_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    severity varchar(16) NOT NULL CHECK (severity IN ('normal','warning','critical')),
    object_kind varchar(80),
    object_namespace varchar(63),
    object_name varchar(253),
    reason_code varchar(80) NOT NULL,
    occurrence_count bigint NOT NULL DEFAULT 1 CHECK (occurrence_count > 0),
    message varchar(1024) NOT NULL
);
CREATE INDEX timeline_events_time_idx
    ON portal.timeline_events (ingested_at DESC, id DESC);
