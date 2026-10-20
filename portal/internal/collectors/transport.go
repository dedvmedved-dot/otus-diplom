package collectors

import (
	"errors"
	"net/http"
	"strings"
)

var (
	errForbiddenMethod = errors.New("transport guard: non-GET method")
	errForbiddenHost   = errors.New("transport guard: non-API-server host")
	errForbiddenScheme = errors.New("transport guard: non-https scheme")
	errRedirect        = errors.New("transport guard: redirect not permitted")
)

// guardTransport enforces the read-only transport contract: GET/HEAD only,
// fixed API server host, https scheme, no redirects, no user-controlled host
// or proxy. RBAC remains the primary boundary; this is defense in depth.
type guardTransport struct {
	base    http.RoundTripper
	apiHost string
}

func newGuardTransport(base http.RoundTripper, apiHost string) *guardTransport {
	if base == nil {
		base = http.DefaultTransport
	}
	return &guardTransport{base: base, apiHost: apiHost}
}

func (g *guardTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	switch req.Method {
	case http.MethodGet, http.MethodHead:
	default:
		return nil, errForbiddenMethod
	}
	if req.URL.Scheme != "https" {
		return nil, errForbiddenScheme
	}
	if g.apiHost != "" && !strings.EqualFold(req.URL.Host, g.apiHost) {
		return nil, errForbiddenHost
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
