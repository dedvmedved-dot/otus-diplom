package collectors

import (
	"errors"
	"net/http"
	"net/url"
	"strings"
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
	"events": true, "endpointslices": true,
}

// key = "group/version/resource".
var approvedGroupResources = map[string]bool{
	"storage.k8s.io/v1/storageclasses":            true,
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
	resp, err := g.base.RoundTrip(req)
	if err != nil {
		return nil, err
	}
	if isRedirect(resp.StatusCode) {
		resp.Body.Close()
		return nil, errRedirect
	}
	return resp, nil
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
