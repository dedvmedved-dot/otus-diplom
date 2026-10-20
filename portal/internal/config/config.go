// Package config loads and validates the Portal runtime configuration.
// All values come from environment variables or mounted secret/CA projections.
// No secrets are embedded in source; the DSN is never logged.
package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// Config is the fully resolved runtime configuration.
type Config struct {
	// Kubernetes
	Namespace string

	// Application database (P8_PORTAL_DB_CONTRACT.md)
	DBHost           string
	DBPort           uint16
	DBName           string
	DBUser           string
	DBSSLMode        string
	DBPasswordFile   string
	DBCACertFile     string
	DBConnectTimeout time.Duration
	DBQueryTimeout   time.Duration
	DBPoolMaxConns   int

	// Auth (single read-only demo operator)
	AuthUsername     string
	AuthVerifierFile string

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
		DBHost:           envOr("PORTAL_DB_HOST", "portal-db-rw.portal.svc"),
		DBPort:           uint16(envIntOr("PORTAL_DB_PORT", 5432)),
		DBName:           envOr("PORTAL_DB_NAME", "portal"),
		DBUser:           envOr("PORTAL_DB_USER", "portal_app"),
		DBSSLMode:        envOr("PORTAL_DB_SSLMODE", "verify-full"),
		DBPasswordFile:   envOr("PORTAL_DB_PASSWORD_FILE", "/etc/portal/db/password"),
		DBCACertFile:     envOr("PORTAL_DB_CA_FILE", "/etc/portal/db/ca.crt"),
		DBConnectTimeout: 5 * time.Second,
		DBQueryTimeout:   3 * time.Second,
		DBPoolMaxConns:   5,
		AuthUsername:     envOr("PORTAL_AUTH_USERNAME", "portal-operator"),
		AuthVerifierFile: envOr("PORTAL_AUTH_VERIFIER_FILE", "/etc/portal/auth/password-sha256"),
		CollectInterval:  envDurationOr("PORTAL_COLLECT_INTERVAL", 30*time.Second),
		MetricsServiceURL: "http://portal-db-metrics.portal.svc:9187/metrics",
		ServerAddr:       envOr("PORTAL_SERVER_ADDR", ":8080"),
		MgmtAddr:         envOr("PORTAL_MGMT_ADDR", ":8081"),
	}

	// Enforce TLS: the demo contract forbids non-TLS fallback.
	if c.DBSSLMode != "verify-full" {
		return nil, fmt.Errorf("DB SSL mode must be verify-full (got %q)", c.DBSSLMode)
	}
	// Enforce host/servername contract; no Pod IP / RO service override.
	if c.DBHost != "portal-db-rw.portal.svc" {
		return nil, fmt.Errorf("DB host must be portal-db-rw.portal.svc (got %q)", c.DBHost)
	}

	if err := requireFile(c.DBPasswordFile); err != nil {
		return nil, fmt.Errorf("DB password projection: %w", err)
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

func envIntOr(key string, def int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
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
