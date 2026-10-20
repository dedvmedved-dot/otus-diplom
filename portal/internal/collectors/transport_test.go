package collectors

import (
	"net/http"
	"testing"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func TestGuardAllowsGetToAPIHost(t *testing.T) {
	base := roundTripFunc(func(req *http.Request) (*http.Response, error) {
		if req.Method != http.MethodGet {
			t.Fatalf("unexpected method %s", req.Method)
		}
		return &http.Response{StatusCode: 200, Body: http.NoBody, Request: req}, nil
	})
	g := newGuardTransport(base, "https://172.30.140.100:6443")
	req, _ := http.NewRequest(http.MethodGet, "https://172.30.140.100:6443/api/v1/nodes", nil)
	resp, err := g.RoundTrip(req)
	if err != nil {
		t.Fatalf("allowed request rejected: %v", err)
	}
	resp.Body.Close()
}

func TestGuardRejectsWrongHost(t *testing.T) {
	g := newGuardTransport(roundTripFunc(func(*http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 200, Body: http.NoBody}, nil
	}), "https://172.30.140.100:6443")
	req, _ := http.NewRequest(http.MethodGet, "https://172.30.140.101:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errForbiddenHost {
		t.Fatalf("expected errForbiddenHost, got %v", err)
	}
}

func TestGuardRejectsWrongScheme(t *testing.T) {
	g := newGuardTransport(roundTripFunc(func(*http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 200, Body: http.NoBody}, nil
	}), "https://172.30.140.100:6443")
	req, _ := http.NewRequest(http.MethodGet, "http://172.30.140.100:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errForbiddenScheme {
		t.Fatalf("expected errForbiddenScheme, got %v", err)
	}
}

func TestGuardRejectsNonGet(t *testing.T) {
	g := newGuardTransport(nil, "https://172.30.140.100:6443")
	req, _ := http.NewRequest(http.MethodPost, "https://172.30.140.100:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errForbiddenMethod {
		t.Fatalf("expected errForbiddenMethod, got %v", err)
	}
}

func TestGuardRejectsForbiddenPath(t *testing.T) {
	g := newGuardTransport(nil, "https://172.30.140.100:6443")
	for _, p := range []string{
		"/api/v1/namespaces/portal/pods/portal-x/log",
		"/api/v1/namespaces/portal/pods/portal-x/exec",
		"/api/v1/namespaces/portal/secrets",
		"/api/v1/namespaces/portal/serviceaccounts/portal-reader/token",
	} {
		req, _ := http.NewRequest(http.MethodGet, "https://172.30.140.100:6443"+p, nil)
		if _, err := g.RoundTrip(req); err != errForbiddenPath {
			t.Fatalf("path %q: expected errForbiddenPath, got %v", p, err)
		}
	}
}

func TestGuardRejectsRedirect(t *testing.T) {
	base := roundTripFunc(func(req *http.Request) (*http.Response, error) {
		return &http.Response{
			StatusCode: http.StatusFound,
			Header:     http.Header{"Location": []string{"http://evil.example/"}},
			Body:       http.NoBody,
			Request:    req,
		}, nil
	})
	g := newGuardTransport(base, "https://172.30.140.100:6443")
	req, _ := http.NewRequest(http.MethodGet, "https://172.30.140.100:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errRedirect {
		t.Fatalf("expected errRedirect, got %v", err)
	}
}
