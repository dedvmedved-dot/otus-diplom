package collectors

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// TestGuardTransportBodyDeadlineReadsBody proves the per-request deadline
// stays alive through body read: a delayed (but < deadline) body is fully read.
func TestGuardTransportBodyDeadlineReadsBody(t *testing.T) {
	old := transportDeadline
	transportDeadline = 2 * time.Second
	defer func() { transportDeadline = old }()

	const body = `{"kind":"NodeList","items":[]}`
	srv := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.(http.Flusher).Flush()
		time.Sleep(300 * time.Millisecond) // delayed body, still inside deadline
		_, _ = w.Write([]byte(body))
	}))
	defer srv.Close()

	gt := newGuardTransport(srv.Client().Transport, srv.URL)
	req, _ := http.NewRequest(http.MethodGet, srv.URL+"/api/v1/nodes", nil)
	resp, err := gt.RoundTrip(req)
	if err != nil {
		t.Fatalf("RoundTrip: %v", err)
	}
	defer resp.Body.Close()
	got, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("body read (deadline must cover body): %v", err)
	}
	if string(got) != body {
		t.Fatalf("body mismatch: got %q", got)
	}
}

// TestGuardTransportBodyDeadlineTimeout proves a body that exceeds the deadline
// fails the read (the request context is still live and cancels the read).
func TestGuardTransportBodyDeadlineTimeout(t *testing.T) {
	old := transportDeadline
	transportDeadline = 200 * time.Millisecond
	defer func() { transportDeadline = old }()

	srv := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.(http.Flusher).Flush()
		time.Sleep(600 * time.Millisecond) // exceeds deadline
		_, _ = w.Write([]byte(`{"items":[]}`))
	}))
	defer srv.Close()

	gt := newGuardTransport(srv.Client().Transport, srv.URL)
	req, _ := http.NewRequest(http.MethodGet, srv.URL+"/api/v1/nodes", nil)
	resp, err := gt.RoundTrip(req)
	if err != nil {
		t.Fatalf("RoundTrip: %v", err)
	}
	defer resp.Body.Close()
	if _, err := io.ReadAll(resp.Body); err == nil {
		t.Fatal("expected body read to fail after deadline")
	}
}

// TestGuardTransportParentCancel proves a cancelled parent context aborts the
// in-flight body read (no leak).
func TestGuardTransportParentCancel(t *testing.T) {
	old := transportDeadline
	transportDeadline = 5 * time.Second
	defer func() { transportDeadline = old }()

	srv := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.(http.Flusher).Flush()
		time.Sleep(500 * time.Millisecond)
		_, _ = w.Write([]byte(`{"items":[]}`))
	}))
	defer srv.Close()

	gt := newGuardTransport(srv.Client().Transport, srv.URL)
	ctx, cancel := context.WithCancel(context.Background())
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, srv.URL+"/api/v1/nodes", nil)
	resp, err := gt.RoundTrip(req)
	if err != nil {
		t.Fatalf("RoundTrip: %v", err)
	}
	cancel() // cancel parent while body is pending
	_, readErr := io.ReadAll(resp.Body)
	resp.Body.Close()
	if readErr == nil {
		t.Fatal("expected body read to fail after parent cancel")
	}
	_ = strings.TrimSpace
}
