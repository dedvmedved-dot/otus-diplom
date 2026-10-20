// Package httpapi implements the read-only Portal HTTP API and static UI.
// GET/HEAD only; unknown paths 404; non-GET/HEAD on known paths 405 (Allow).
// No mutation, no generic proxy, no user-controlled Kubernetes path.
package httpapi

import (
	"encoding/json"
	"io/fs"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/auth"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/store"
	"github.com/dedvmedved-dot/otus-diplom/portal/web"
)

// Server holds the wired dependencies for the HTTP layer.
type Server struct {
	collector *collectors.Collector
	store     *store.Store
	verifier  *auth.Verifier
	cfg       *config.Config
	ps        *collectors.PersistenceState
	rate      *tokenBucket
	sem       chan struct{}
}

// New builds a Server.
func New(c *collectors.Collector, st *store.Store, v *auth.Verifier, cfg *config.Config, ps *collectors.PersistenceState) *Server {
	return &Server{
		collector: c,
		store:     st,
		verifier:  v,
		cfg:       cfg,
		ps:        ps,
		rate:      newTokenBucket(50),
		sem:       make(chan struct{}, 20),
	}
}

// apiRoutes maps path -> handler (fixed allowlist; no dynamic routing).
func (s *Server) apiRoutes() map[string]http.HandlerFunc {
	return map[string]http.HandlerFunc{
		"/api/v1/health":    s.handleHealth,
		"/api/v1/summary":   s.handleSummary,
		"/api/v1/nodes":     s.handleNodes,
		"/api/v1/workloads": s.handleWorkloads,
		"/api/v1/pods":      s.handlePods,
		"/api/v1/services":  s.handleServices,
		"/api/v1/storage":   s.handleStorage,
		"/api/v1/backups":   s.handleBackups,
		"/api/v1/database":  s.handleDatabase,
		"/api/v1/metrics":   s.handleMetrics,
		"/api/v1/events":    s.handleEvents,
	}
}

// Handler assembles the full middleware chain.
func (s *Server) Handler() http.Handler {
	return s.securityHeaders(s.concurrencyLimit(s.rateLimit(s.auth(http.HandlerFunc(s.route)))))
}

// route dispatches known API/asset paths and rejects everything else with 404/405.
func (s *Server) route(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	if h, ok := s.apiRoutes()[path]; ok {
		if r.Method != http.MethodGet && r.Method != http.MethodHead {
			w.Header().Set("Allow", "GET, HEAD")
			writeError(w, http.StatusMethodNotAllowed, "METHOD_NOT_ALLOWED", "method not allowed")
			return
		}
		h(w, r)
		return
	}

	if path == "/" {
		s.handleIndex(w, r)
		return
	}
	if strings.HasPrefix(path, "/assets/") {
		if r.Method != http.MethodGet && r.Method != http.MethodHead {
			w.Header().Set("Allow", "GET, HEAD")
			writeError(w, http.StatusMethodNotAllowed, "METHOD_NOT_ALLOWED", "method not allowed")
			return
		}
		s.handleAssets(w, r)
		return
	}

	writeError(w, http.StatusNotFound, "NOT_FOUND", "unknown path")
}

// tokenBucket is a minimal fixed-rate limiter.
type tokenBucket struct {
	tokens chan struct{}
}

func newTokenBucket(rps int) *tokenBucket {
	tb := &tokenBucket{tokens: make(chan struct{}, rps)}
	go func() {
		t := time.NewTicker(time.Second / time.Duration(rps))
		defer t.Stop()
		for range t.C {
			select {
			case tb.tokens <- struct{}{}:
			default:
			}
		}
	}()
	return tb
}

func (tb *tokenBucket) allow() bool {
	select {
	case <-tb.tokens:
		return true
	default:
		return false
	}
}

func (s *Server) concurrencyLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case s.sem <- struct{}{}:
			defer func() { <-s.sem }()
			next.ServeHTTP(w, r)
		default:
			writeError(w, http.StatusServiceUnavailable, "UNAVAILABLE", "concurrency limit reached")
		}
	})
}

func (s *Server) rateLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !s.rate.allow() {
			writeError(w, http.StatusTooManyRequests, "RATE_LIMITED", "too many requests")
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *Server) auth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user, pass, ok := r.BasicAuth()
		if !ok || !s.verifier.Verify(user, pass) {
			w.Header().Set("WWW-Authenticate", `Basic realm="portal"`)
			writeError(w, http.StatusUnauthorized, "UNAUTHORIZED", "missing or invalid operator credentials")
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *Server) securityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		h := w.Header()
		h.Set("Referrer-Policy", "no-referrer")
		h.Set("X-Content-Type-Options", "nosniff")
		h.Set("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
		h.Set("Cache-Control", "no-cache")
		next.ServeHTTP(w, r)
	})
}

func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	b, err := web.FS.ReadFile("index.html")
	if err != nil {
		writeError(w, http.StatusInternalServerError, "UNAVAILABLE", "index unavailable")
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = w.Write(b)
}

func (s *Server) handleAssets(w http.ResponseWriter, r *http.Request) {
	sub, err := fs.Sub(web.FS, ".")
	if err != nil {
		writeError(w, http.StatusInternalServerError, "UNAVAILABLE", "assets unavailable")
		return
	}
	http.StripPrefix("/assets/", http.FileServer(http.FS(sub))).ServeHTTP(w, r)
}

func writeJSON(w http.ResponseWriter, code int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-cache")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(body)
}

// writeError emits a bounded, fixed-code error body (never raw error text).
func writeError(w http.ResponseWriter, code int, errCode, msg string) {
	if len(msg) > 256 {
		msg = msg[:256]
	}
	writeJSON(w, code, model.Error{
		RequestID:   newRequestID(),
		GeneratedAt: time.Now().UTC().Format(time.RFC3339),
		Code:        errCode,
		Message:     msg,
	})
}

var _ = sync.Mutex{}
