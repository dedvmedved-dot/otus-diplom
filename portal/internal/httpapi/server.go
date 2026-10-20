// Package httpapi implements the read-only Portal HTTP API and static UI.
// GET/HEAD only; unknown paths 404; non-GET/HEAD on known paths 405;
// no mutation, no generic proxy, no user-controlled Kubernetes path.
package httpapi

import (
	"encoding/json"
	"io/fs"
	"net/http"
	"sync"
	"time"

	"github.com/dedvmedved-dot/otus-diplom/portal/internal/auth"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/config"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/store"
	"github.com/dedvmedved-dot/otus-diplom/portal/web"
)

// Server holds the wired dependencies for the HTTP layer.
type Server struct {
	collector *collectors.Collector
	store     *store.Store
	verifier  *auth.Verifier
	cfg       *config.Config
	rate      *tokenBucket
	sem       chan struct{}
}

// New builds a Server.
func New(c *collectors.Collector, st *store.Store, v *auth.Verifier, cfg *config.Config) *Server {
	return &Server{
		collector: c,
		store:     st,
		verifier:  v,
		cfg:       cfg,
		rate:      newTokenBucket(50),
		sem:       make(chan struct{}, 20),
	}
}

// Handler assembles the full middleware chain.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /api/v1/health", s.handleHealth)
	mux.HandleFunc("GET /api/v1/summary", s.handleSummary)
	mux.HandleFunc("GET /api/v1/nodes", s.handleNodes)
	mux.HandleFunc("GET /api/v1/workloads", s.handleWorkloads)
	mux.HandleFunc("GET /api/v1/pods", s.handlePods)
	mux.HandleFunc("GET /api/v1/services", s.handleServices)
	mux.HandleFunc("GET /api/v1/storage", s.handleStorage)
	mux.HandleFunc("GET /api/v1/backups", s.handleBackups)
	mux.HandleFunc("GET /api/v1/database", s.handleDatabase)
	mux.HandleFunc("GET /api/v1/metrics", s.handleMetrics)
	mux.HandleFunc("GET /api/v1/events", s.handleEvents)

	mux.HandleFunc("GET /", s.handleIndex)
	mux.HandleFunc("GET /assets/", s.handleAssets)

	return s.securityHeaders(s.concurrencyLimit(s.rateLimit(s.auth(mux))))
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

// concurrencyLimit bounds simultaneous in-flight requests.
func (s *Server) concurrencyLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case s.sem <- struct{}{}:
			defer func() { <-s.sem }()
			next.ServeHTTP(w, r)
		default:
			writeError(w, http.StatusServiceUnavailable, "TOO_MANY_CONCURRENT", "concurrency limit reached")
		}
	})
}

// rateLimit rejects requests beyond the global rate bound.
func (s *Server) rateLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !s.rate.allow() {
			writeError(w, http.StatusTooManyRequests, "RATE_LIMITED", "too many requests")
			return
		}
		next.ServeHTTP(w, r)
	})
}

// auth enforces Basic Auth on every route.
func (s *Server) auth(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		user, pass, ok := r.BasicAuth()
		if !ok || !s.verifier.Verify(user, pass) {
			w.Header().Set("WWW-Authenticate", `Basic realm="portal"`)
			writeError(w, http.StatusUnauthorized, "UNAUTHENTICATED", "missing or invalid operator credentials")
			return
		}
		next.ServeHTTP(w, r)
	})
}

// securityHeaders sets the fixed CSP and transport headers.
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

// handleIndex serves the single-page shell.
func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		writeError(w, http.StatusNotFound, "NOT_FOUND", "unknown path")
		return
	}
	b, err := web.FS.ReadFile("index.html")
	if err != nil {
		writeError(w, http.StatusInternalServerError, "ASSET_ERROR", "index unavailable")
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = w.Write(b)
}

// handleAssets serves embedded static assets (immutable, content-hashed names).
func (s *Server) handleAssets(w http.ResponseWriter, r *http.Request) {
	sub, err := fs.Sub(web.FS, ".")
	if err != nil {
		writeError(w, http.StatusInternalServerError, "ASSET_ERROR", "assets unavailable")
		return
	}
	// Only allow direct file paths under /assets/.
	http.StripPrefix("/assets/", http.FileServer(http.FS(sub))).ServeHTTP(w, r)
}

// writeJSON emits an envelope/JSON response with no-cache.
func writeJSON(w http.ResponseWriter, code int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-cache")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(body)
}

// writeError emits a sanitized error body.
func writeError(w http.ResponseWriter, code int, errorCode, msg string) {
	writeJSON(w, code, map[string]any{"errorCode": errorCode, "message": msg})
}

var _ = sync.Mutex{}
