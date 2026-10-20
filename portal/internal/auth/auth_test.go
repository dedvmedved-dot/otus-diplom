package auth

import (
	"crypto/sha256"
	"encoding/hex"
	"testing"
)

func TestVerifier(t *testing.T) {
	pass := "correct-horse-battery-staple-0000"
	sum := sha256.Sum256([]byte(pass))
	v, err := NewVerifier("portal-operator", hex.EncodeToString(sum[:]))
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
	if _, err := NewVerifier("u", "too-short"); err == nil {
		t.Fatal("expected error for short verifier")
	}
}
