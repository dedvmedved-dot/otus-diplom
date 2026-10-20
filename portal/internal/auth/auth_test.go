package auth

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"testing"
)

func TestVerifier(t *testing.T) {
	dir := t.TempDir()
	pass := "correct-horse-battery-staple-0000"
	sum := sha256.Sum256([]byte(pass))
	f := filepath.Join(dir, "verifier")
	if err := os.WriteFile(f, []byte(hex.EncodeToString(sum[:])), 0o600); err != nil {
		t.Fatal(err)
	}
	v, err := NewVerifier("portal-operator", f)
	if err != nil {
		t.Fatal(err)
	}
	if !v.Verify("portal-operator", pass) {
		t.Fatal("expected valid credentials")
	}
	if v.Verify("portal-operator", "wrong") {
		t.Fatal("expected invalid password to be rejected")
	}
	if v.Verify("admin", pass) {
		t.Fatal("expected invalid username to be rejected")
	}
}

func TestVerifierRejectsShortVerifier(t *testing.T) {
	dir := t.TempDir()
	f := filepath.Join(dir, "v")
	if err := os.WriteFile(f, []byte("too-short"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := NewVerifier("u", f); err == nil {
		t.Fatal("expected error for short verifier")
	}
}
