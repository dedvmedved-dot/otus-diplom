// Package auth implements single read-only demo operator Basic Auth.
// The stored verifier is the hex SHA-256 of a high-entropy random password;
// comparison is constant-time. The Authorization header is never logged.
package auth

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"os"
	"strings"
)

// Verifier holds the expected operator username and password verifier.
type Verifier struct {
	username string
	sumHex   string
}

// NewVerifier reads the verifier (hex SHA-256) from a mounted secret file.
func NewVerifier(username, verifierFile string) (*Verifier, error) {
	raw, err := os.ReadFile(verifierFile)
	if err != nil {
		return nil, err
	}
	sumHex := strings.TrimSpace(string(raw))
	if len(sumHex) != 64 {
		return nil, errBadVerifier
	}
	if _, err := hex.DecodeString(sumHex); err != nil {
		return nil, errBadVerifier
	}
	return &Verifier{username: username, sumHex: strings.ToLower(sumHex)}, nil
}

var errBadVerifier = &verifierError{}

type verifierError struct{}

func (verifierError) Error() string { return "invalid auth verifier" }

// Verify checks a username/password pair in constant time.
func (v *Verifier) Verify(username, password string) bool {
	sum := sha256.Sum256([]byte(password))
	got := hex.EncodeToString(sum[:])
	userOK := subtle.ConstantTimeCompare([]byte(username), []byte(v.username)) == 1
	passOK := subtle.ConstantTimeCompare([]byte(got), []byte(v.sumHex)) == 1
	return userOK && passOK
}

// Middleware wraps an http.Handler with Basic Auth enforcement.
func (v *Verifier) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user, pass, ok := r.BasicAuth()
		if !ok || !v.Verify(user, pass) {
			w.Header().Set("WWW-Authenticate", `Basic realm="portal"`)
			writeJSON(w, http.StatusUnauthorized, map[string]any{
				"errorCode": "UNAUTHENTICATED",
				"message":   "missing or invalid operator credentials",
			})
			return
		}
		next.ServeHTTP(w, r)
	})
}

func writeJSON(w http.ResponseWriter, code int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	enc, _ := json.Marshal(body)
	_, _ = w.Write(enc)
}
