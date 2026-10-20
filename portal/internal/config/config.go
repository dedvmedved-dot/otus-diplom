// Package config loads and validates the Portal runtime configuration.
// DB identity is fixed (no ambient overrides). The DB password and auth
// verifier arrive via secretKeyRef env values and are never logged/dumped.
// The public DB CA arrives via a mount projection (no private keys).
package config

import (
	"fmt"
	"os"
	"time"
)

// Fixed DB contract (P8_PORTAL_DB_CONTRACT.md). No env override is permitted.
const (
	DBHost    = "portal-db-rw.portal.svc"
	DBPort    = 5432
	DBName    = "portal"
	DBUser    = "portal_app"
	DBSSLMode = "verify-full"
)

// Config is the fully resolved runtime configuration.
type Config struct {
	// Kubernetes
	Namespace string

	// Fixed DB identity (constants above); secret material below.
	DBPassword     string
	DBCACertFile   string
	DBConnectTimeout time.Duration
	DBQueryTimeout time.Duration
	DBPoolMaxConns int

	// Auth (single read-only demo operator)
	AuthUsername   string
	AuthVerifier   string // hex SHA-256 of the operator password (from secretKeyRef)

	// Collection
	CollectInterval   time.Duration
	MetricsServiceURL string

	// Listening addresses
	ServerAddr string
	MgmtAddr   string

	// Build metadata (set at build time via ldflags)
	SourceRevision string
	BuildTime      string
}

// Load reads configuration from the environment and validates it.
// It never logs or prints secret material.
func Load() (*Config, error) {
	c := &Config{
		Namespace:        envOr("PORTAL_NAMESPACE", "portal"),
		DBPassword:       os.Getenv("PORTAL_DB_PASSWORD"),
		DBCACertFile:     envOr("PORTAL_DB_CA_FILE", "/etc/portal/db/ca.crt"),
		DBConnectTimeout: 5 * time.Second,
		DBQueryTimeout:   3 * time.Second,
		DBPoolMaxConns:   5,
		AuthUsername:     envOr("PORTAL_AUTH_USERNAME", "portal-operator"),
		AuthVerifier:     os.Getenv("PORTAL_AUTH_VERIFIER"),
		CollectInterval:  envDurationOr("PORTAL_COLLECT_INTERVAL", 30*time.Second),
		MetricsServiceURL: envOr("PORTAL_METRICS_URL", "http://portal-db-metrics.portal.svc:9187/metrics"),
		ServerAddr:       envOr("PORTAL_SERVER_ADDR", ":8080"),
		MgmtAddr:         envOr("PORTAL_MGMT_ADDR", ":8081"),
	}

	if c.DBPassword == "" {
		return nil, fmt.Errorf("PORTAL_DB_PASSWORD (secretKeyRef portal-db-app/password) is required")
	}
	if err := requireFile(c.DBCACertFile); err != nil {
		return nil, fmt.Errorf("DB CA projection: %w", err)
	}
	return c, nil
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func envDurationOr(key string, def time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return def
}

func requireFile(path string) error {
	fi, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("%s: %w", path, err)
	}
	if fi.IsDir() {
		return fmt.Errorf("%s is a directory", path)
	}
	return nil
}
