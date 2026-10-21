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

// Approved collection paths. The guard is an EXACT allowlist: any resource not
// listed here, any namespace/name shape outside the approved grammar, or any
// subresource segment is rejected. RBAC remains the primary boundary.
var approvedCoreResources = map[string]bool{
	"nodes": true, "pods": true, "services": true,
	"persistentvolumeclaims": true, "persistentvolumes": true,
	"events": true,
}

// key = "group/version/resource".
var approvedGroupResources = map[string]bool{
	"storage.k8s.io/v1/storageclasses":            true,
	"discovery.k8s.io/v1/endpointslices":          true,
	"apps/v1/deployments":                         true,
	"apps/v1/statefulsets":                        true,
	"apps/v1/daemonsets":                          true,
	"apps/v1/replicasets":                         true,
	"batch/v1/jobs":                               true,
	"batch/v1/cronjobs":                           true,
	"snapshot.storage.k8s.io/v1/volumesnapshots":  true,
	"metrics.k8s.io/v1beta1/nodes":                true,
	"metrics.k8s.io/v1beta1/pods":                 true,
	"postgresql.cnpg.io/v1/clusters":              true,
	"postgresql.cnpg.io/v1/scheduledbackups":      true,
	"postgresql.cnpg.io/v1/backups":               true,
	"barmancloud.cnpg.io/v1/objectstores":         true,
	"velero.io/v1/backupstoragelocations":         true,
	"velero.io/v1/backups":                        true,
	"velero.io/v1/restores":                       true,
	"gateway.networking.k8s.io/v1/gateways":       true,
	"gateway.networking.k8s.io/v1/httproutes":     true,
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
	if u, err := url.Parse(apiURL); err == nil {
		host = u.Host
		if u.Scheme != "" {
			scheme = u.Scheme
		}
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
	if !pathAllowed(req.URL.Path) {
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
func pathAllowed(path string) bool {
	if path == "" || path[0] != '/' {
		return false
	}
	segs := strings.Split(strings.Trim(path, "/"), "/")

	if len(segs) >= 2 && segs[0] == "api" && segs[1] == "v1" {
		rest := segs[2:]
		if len(rest) >= 1 && rest[0] == "namespaces" {
			if len(rest) < 3 || !approvedCoreResources[rest[2]] {
				return false
			}
			return len(rest) <= 4 // /api/v1/namespaces/{ns}/{res}[/{name}]
		}
		if len(rest) >= 1 && approvedCoreResources[rest[0]] {
			return len(rest) <= 2 // /api/v1/{res}[/{name}]
		}
		return false
	}

	if len(segs) >= 3 && segs[0] == "apis" {
		groupVer := segs[1] + "/" + segs[2]
		rest := segs[3:]
		var res string
		if len(rest) >= 1 && rest[0] == "namespaces" {
			if len(rest) < 3 {
				return false
			}
			res = rest[2]
			if len(rest) > 4 {
				return false // subresource
			}
		} else if len(rest) >= 1 {
			res = rest[0]
			if len(rest) > 2 {
				return false
			}
		} else {
			return false
		}
		return approvedGroupResources[groupVer+"/"+res]
	}
	return false
}
