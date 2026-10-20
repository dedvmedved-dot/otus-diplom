package collectors

import (
	"net/http"
	"testing"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func okBase() http.RoundTripper {
	return roundTripFunc(func(r *http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 200, Body: http.NoBody, Request: r}, nil
	})
}

func TestGuardAllowsApprovedPaths(t *testing.T) {
	paths := []string{
		"/api/v1/nodes",
		"/api/v1/nodes/node-01",
		"/api/v1/pods",
		"/api/v1/namespaces/portal/pods",
		"/api/v1/namespaces/portal/services/portal-db-rw",
		"/api/v1/persistentvolumeclaims",
		"/api/v1/events",
		"/apis/discovery.k8s.io/v1/endpointslices",
		"/apis/discovery.k8s.io/v1/namespaces/portal/endpointslices",
		"/apis/apps/v1/deployments",
		"/apis/apps/v1/namespaces/portal/statefulsets",
		"/apis/batch/v1/jobs",
		"/apis/batch/v1/cronjobs",
		"/apis/storage.k8s.io/v1/storageclasses",
		"/apis/snapshot.storage.k8s.io/v1/volumesnapshots",
		"/apis/metrics.k8s.io/v1beta1/nodes",
		"/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters",
		"/apis/postgresql.cnpg.io/v1/namespaces/portal/scheduledbackups",
		"/apis/postgresql.cnpg.io/v1/namespaces/portal/backups",
		"/apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores",
		"/apis/velero.io/v1/backupstoragelocations",
		"/apis/velero.io/v1/backups",
		"/apis/gateway.networking.k8s.io/v1/gateways",
	}
	g := newGuardTransport(okBase(), "https://10.0.0.1:6443")
	for _, p := range paths {
		req, _ := http.NewRequest(http.MethodGet, "https://10.0.0.1:6443"+p, nil)
		if _, err := g.RoundTrip(req); err != nil {
			t.Fatalf("approved path %s rejected: %v", p, err)
		}
	}
}

func TestGuardRejectsUnapprovedPaths(t *testing.T) {
	paths := []string{
		"/api/v1/configmaps",                          // unapproved core resource
		"/api/v1/endpointslices",                      // wrong: endpointslices is a grouped resource
		"/api/v1/secrets",                             // secrets
		"/api/v1/namespaces/portal/secrets",           // secrets in namespace
		"/api/v1/serviceaccounts/portal/token",        // token subresource
		"/api/v1/namespaces/portal/pods/x/log",        // log subresource
		"/api/v1/namespaces/portal/pods/x/exec",       // exec subresource
		"/apis/rbac.authorization.k8s.io/v1/roles",    // unapproved GVR
		"/apis/apps/v1/namespaces/portal/deployments/x/status", // status subresource
		"/apis/core/v1/nodes",                         // wrong group
		"/api/v1/namespaces/portal/pods/x/proxy",      // proxy
	}
	g := newGuardTransport(okBase(), "https://10.0.0.1:6443")
	for _, p := range paths {
		req, _ := http.NewRequest(http.MethodGet, "https://10.0.0.1:6443"+p, nil)
		if _, err := g.RoundTrip(req); err != errForbiddenPath {
			t.Fatalf("unapproved path %s: expected errForbiddenPath, got %v", p, err)
		}
	}
}

func TestGuardRejectsWrongHost(t *testing.T) {
	g := newGuardTransport(okBase(), "https://10.0.0.1:6443")
	req, _ := http.NewRequest("GET", "https://10.0.0.2:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errForbiddenHost {
		t.Fatalf("expected errForbiddenHost, got %v", err)
	}
}

func TestGuardRejectsHostOverride(t *testing.T) {
	g := newGuardTransport(okBase(), "https://10.0.0.1:6443")
	req, _ := http.NewRequest("GET", "https://10.0.0.1:6443/api/v1/nodes", nil)
	req.Host = "evil.example.com"
	if _, err := g.RoundTrip(req); err != errForbiddenHost {
		t.Fatalf("expected errForbiddenHost for Host override, got %v", err)
	}
}

func TestGuardRejectsUserinfo(t *testing.T) {
	g := newGuardTransport(okBase(), "https://10.0.0.1:6443")
	req, _ := http.NewRequest("GET", "https://user@10.0.0.1:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errForbiddenHost {
		t.Fatalf("expected errForbiddenHost for userinfo, got %v", err)
	}
}

func TestGuardRejectsEmptyHost(t *testing.T) {
	g := newGuardTransport(okBase(), "")
	req, _ := http.NewRequest("GET", "https://10.0.0.1:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errForbiddenHost {
		t.Fatalf("expected errForbiddenHost for empty configured host, got %v", err)
	}
}

func TestGuardRejectsPost(t *testing.T) {
	g := newGuardTransport(okBase(), "https://10.0.0.1:6443")
	req, _ := http.NewRequest("POST", "https://10.0.0.1:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errForbiddenMethod {
		t.Fatalf("expected errForbiddenMethod, got %v", err)
	}
}

func TestGuardRejectsRedirect(t *testing.T) {
	base := roundTripFunc(func(req *http.Request) (*http.Response, error) {
		return &http.Response{StatusCode: 302, Header: http.Header{"Location": []string{"/other"}}, Body: http.NoBody, Request: req}, nil
	})
	g := newGuardTransport(base, "https://10.0.0.1:6443")
	req, _ := http.NewRequest("GET", "https://10.0.0.1:6443/api/v1/nodes", nil)
	if _, err := g.RoundTrip(req); err != errRedirect {
		t.Fatalf("expected errRedirect, got %v", err)
	}
}
