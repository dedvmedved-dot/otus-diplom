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
	errForbiddenPath   = errors.New("transport guard: forbidden path/subresource")
	errRedirect        = errors.New("transport guard: redirect not permitted")
)

// guardTransport enforces the read-only transport contract: GET/HEAD only,
// fixed API server authority (scheme + host:port, parsed from the canonical
// base URL), no forbidden subresource paths, no redirects. RBAC remains the
// primary boundary; this is defense in depth.
type guardTransport struct {
	base    http.RoundTripper
	apiHost string // authority "host:port" (no scheme, no userinfo)
	scheme  string // "https"
}

// newGuardTransport parses the canonical API base URL once. client-go
// InClusterConfig sets Host to "https://<host>:<port>"; req.URL.Host is only
// "<host>:<port>", so the authority is compared without the scheme.
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
	switch req.Method {
	case http.MethodGet, http.MethodHead:
	default:
		return nil, errForbiddenMethod
	}
	if req.URL.Scheme != g.scheme {
		return nil, errForbiddenScheme
	}
	if g.apiHost != "" && !strings.EqualFold(req.URL.Host, g.apiHost) {
		return nil, errForbiddenHost
	}
	if forbiddenPath(req.URL.Path) {
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

// forbiddenPath rejects proxy/log/exec/attach/portforward, Secret reads and
// SA token subresources. Only exact path segments are matched.
func forbiddenPath(path string) bool {
	for _, seg := range strings.Split(path, "/") {
		switch seg {
		case "proxy", "log", "exec", "attach", "portforward", "secrets", "token":
			return true
		}
	}
	return false
}

func isRedirect(code int) bool {
	switch code {
	case http.StatusMovedPermanently, http.StatusFound, http.StatusSeeOther,
		http.StatusTemporaryRedirect, http.StatusPermanentRedirect:
		return true
	}
	return false
}
