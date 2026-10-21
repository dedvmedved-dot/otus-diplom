package collectors

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

var (
	errForbiddenMethod = errors.New("transport guard: non-GET method")
	errForbiddenHost   = errors.New("transport guard: non-API-server host")
	errForbiddenScheme = errors.New("transport guard: non-https scheme")
	errForbiddenPath   = errors.New("transport guard: unapproved path/subresource")
	errRedirect        = errors.New("transport guard: redirect not permitted")
)

// Exact paths actually consumed by the read-only collectors. Namespace-scoped
// privileged domains have no wildcard names or namespaces.
var approvedPaths = map[string]bool{
	"/api/v1/nodes":                                                    true,
	"/api/v1/pods":                                                     true,
	"/api/v1/services":                                                 true,
	"/api/v1/persistentvolumeclaims":                                   true,
	"/api/v1/persistentvolumes":                                        true,
	"/api/v1/events":                                                   true,
	"/apis/storage.k8s.io/v1/storageclasses":                           true,
	"/apis/discovery.k8s.io/v1/endpointslices":                         true,
	"/apis/apps/v1/deployments":                                        true,
	"/apis/apps/v1/statefulsets":                                       true,
	"/apis/apps/v1/daemonsets":                                         true,
	"/apis/apps/v1/replicasets":                                        true,
	"/apis/batch/v1/jobs":                                              true,
	"/apis/batch/v1/cronjobs":                                          true,
	"/apis/snapshot.storage.k8s.io/v1/volumesnapshots":                 true,
	"/apis/metrics.k8s.io/v1beta1/nodes":                               true,
	"/apis/metrics.k8s.io/v1beta1/pods":                                true,
	"/apis/postgresql.cnpg.io/v1/namespaces/portal/clusters/portal-db": true,
	"/apis/postgresql.cnpg.io/v1/namespaces/portal/scheduledbackups/portal-db-daily": true,
	"/apis/postgresql.cnpg.io/v1/namespaces/portal/backups":                          true,
	"/apis/barmancloud.cnpg.io/v1/namespaces/portal/objectstores/portal-db-backup":   true,
	"/apis/velero.io/v1/namespaces/velero/backupstoragelocations":                    true,
	"/apis/velero.io/v1/namespaces/velero/backups":                                   true,
	"/apis/velero.io/v1/namespaces/velero/restores":                                  true,
	"/apis/gateway.networking.k8s.io/v1/namespaces/portal/gateways/portal-gateway":   true,
	"/apis/gateway.networking.k8s.io/v1/namespaces/portal/httproutes/portal":         true,
}

// transportDeadline is the per-request deadline. Overridable in tests only.
var transportDeadline = 5 * time.Second

type guardTransport struct {
	base    http.RoundTripper
	apiHost string // host:port, no scheme; empty means guard rejects everything
	scheme  string // "https"
}

func newGuardTransport(base http.RoundTripper, apiURL string) *guardTransport {
	if base == nil {
		base = http.DefaultTransport
	}
	host := ""
	scheme := "https"
	if u, err := url.Parse(apiURL); err == nil && u.Scheme == "https" && u.Hostname() != "" && u.User == nil && u.Path == "" && u.RawQuery == "" && u.Fragment == "" {
		host = u.Host
	}
	return &guardTransport{base: base, apiHost: host, scheme: scheme}
}

func (g *guardTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	if req.Method != http.MethodGet && req.Method != http.MethodHead {
		return nil, errForbiddenMethod
	}
	if req.URL.Scheme != g.scheme {
		return nil, errForbiddenScheme
	}
	if g.apiHost == "" {
		return nil, errForbiddenHost // fail closed on empty parsed host
	}
	if req.URL.User != nil {
		return nil, errForbiddenHost // userinfo forbidden
	}
	if !strings.EqualFold(req.URL.Host, g.apiHost) {
		return nil, errForbiddenHost
	}
	// Host header override (req.Host) must also match the API authority.
	if req.Host != "" && !strings.EqualFold(req.Host, g.apiHost) {
		return nil, errForbiddenHost
	}
	if req.URL.RawPath != "" || !pathAllowed(req.URL.Path) {
		return nil, errForbiddenPath
	}
	// Per-request deadline (5s) inside the 20s collection cycle. The deadline
	// must cover the WHOLE request including body read, so the cancel is tied
	// to the body's Read/Close (EOF) rather than to RoundTrip's return.
	ctx, cancel := context.WithTimeout(req.Context(), transportDeadline)
	resp, err := g.base.RoundTrip(req.WithContext(ctx))
	if err != nil {
		cancel()
		return nil, err
	}
	if isRedirect(resp.StatusCode) {
		resp.Body.Close()
		cancel()
		return nil, errRedirect
	}
	resp.Body = &deadlineBody{rc: resp.Body, cancel: cancel}
	return resp, nil
}

// deadlineBody keeps the per-request deadline alive until the response body is
// fully read (EOF/error) or explicitly closed, then cancels the context.
type deadlineBody struct {
	rc     io.ReadCloser
	cancel context.CancelFunc
	once   sync.Once
}

func (b *deadlineBody) Read(p []byte) (int, error) {
	n, err := b.rc.Read(p)
	if err != nil {
		b.once.Do(b.cancel)
	}
	return n, err
}

func (b *deadlineBody) Close() error {
	b.once.Do(b.cancel)
	return b.rc.Close()
}

func isRedirect(code int) bool {
	switch code {
	case http.StatusMovedPermanently, http.StatusFound, http.StatusSeeOther,
		http.StatusTemporaryRedirect, http.StatusPermanentRedirect:
		return true
	}
	return false
}

// pathAllowed enforces the exact approved path grammar. Unknown resources,
// subresources, and namespaces/names outside the grammar are rejected.
func pathAllowed(path string) bool { return approvedPaths[path] }
