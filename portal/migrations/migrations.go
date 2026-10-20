// Package migrations embeds the versioned forward-only application schema
// migrations and exposes their SHA-256 checksums for the migration ledger.
package migrations

import (
	"crypto/sha256"
	_ "embed"
	"encoding/hex"
)

//go:embed 0001_portal_observations.sql
var SQL0001 string

// Version0001 is the schema version for the observations migration.
const Version0001 int64 = 1

// Checksum0001 returns the hex SHA-256 of the version-1 migration SQL.
func Checksum0001() string {
	s := sha256.Sum256([]byte(SQL0001))
	return hex.EncodeToString(s[:])
}
