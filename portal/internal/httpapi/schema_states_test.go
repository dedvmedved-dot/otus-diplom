package httpapi

import (
	"encoding/json"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/model"
	"net/http/httptest"
	"testing"
	"time"
)

func TestSchemaActualStartupStalePartialFailure(t *testing.T) {
	oa := loadOpenAPI(t)
	for _, state := range []string{"startup", "stale", "unavailable", "partial", "persistence-failure"} {
		t.Run(state, func(t *testing.T) {
			srv := contractTestServer()
			snap := srv.collector.Latest()
			switch state {
			case "startup":
				srv.collector = mockSnapshotProvider{nil}
			case "stale":
				snap.CollectedAt = time.Now().Add(-2 * time.Minute)
			case "unavailable":
				snap.CollectedAt = time.Now().Add(-10 * time.Minute)
			case "partial":
				snap.Partial = true
			case "persistence-failure":
				srv.store = failStore{}
				srv.ps = &collectors.PersistenceState{}
				srv.ps.Failed.Store(true)
				snap.Events = []model.TimelineEvent{{ID: "test-event", Source: "kubernetes", Severity: "normal", ReasonCode: "Started", Message: "fixture", OccurrenceCount: 1}}
			}
			for path := range srv.apiRoutes() {
				code, body := doGet(t, srv.Handler(), path)
				if code != 200 {
					t.Fatalf("%s %d", path, code)
				}
				for _, err := range validateAgainstSchema(oa, path, "response", schemaFor(t, oa, path), body) {
					t.Error(err)
				}
				if path == "/api/v1/health" && state != "partial" && state != "stale" && state != "unavailable" {
					if body["data"].(map[string]any)["persistenceLagSeconds"] != nil {
						t.Fatal("no successful write must be null")
					}
				}
				if path == "/api/v1/health" && state != "startup" && body["data"].(map[string]any)["status"] == "healthy" {
					t.Fatal("degraded view is healthy")
				}
			}
		})
	}
}
func TestSchemaDrivenErrorResponses(t *testing.T) {
	oa := loadOpenAPI(t)
	schema := map[string]any{"$ref": "#/components/schemas/Error"}
	for _, test := range []struct {
		name, method, path string
		status             int
	}{
		{"bad-query", "GET", "/api/v1/nodes?bad=x", 400}, {"unauthorized", "GET", "/api/v1/nodes", 401},
		{"unknown", "GET", "/api/v1/unknown", 404}, {"method", "POST", "/api/v1/nodes", 405},
		{"rate", "GET", "/api/v1/nodes", 429}, {"concurrency", "GET", "/api/v1/nodes", 503},
		{"cursor", "GET", "/api/v1/nodes?cursor=bad", 400},
	} {
		t.Run(test.name, func(t *testing.T) {
			srv := contractTestServer()
			if test.name == "rate" {
				srv.rate = &tokenBucket{tokens: make(chan struct{})}
			}
			if test.name == "concurrency" {
				srv.sem = make(chan struct{})
			}
			req := httptest.NewRequest(test.method, test.path, nil)
			if test.name != "unauthorized" {
				req.SetBasicAuth("portal-operator", "test-password")
			}
			rr := httptest.NewRecorder()
			srv.Handler().ServeHTTP(rr, req)
			if rr.Code != test.status {
				t.Fatalf("want %d got %d", test.status, rr.Code)
			}
			var body any
			if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
				t.Fatal(err)
			}
			for _, err := range validateAgainstSchema(oa, test.path, "error", schema, body) {
				t.Error(err)
			}
		})
	}
}
func TestSchemaConstraintNegatives(t *testing.T) {
	oa := loadOpenAPI(t)
	tests := []struct {
		schema map[string]any
		value  any
	}{
		{map[string]any{"type": "number", "minimum": 0}, float64(-1)},
		{map[string]any{"type": "string", "format": "date-time"}, ""},
		{map[string]any{"type": "string", "pattern": "^[a-f0-9]{40}$"}, "invalid"},
		{map[string]any{"type": "string", "maxLength": 2}, "абв"},
		{map[string]any{"type": "array", "maxItems": 1}, []any{1, 2}},
		{map[string]any{"$ref": "#/components/schemas/Absent"}, nil},
		{map[string]any{"$ref": "https://outside.invalid/schema"}, nil},
		{map[string]any{"anyOf": []any{map[string]any{"type": "null"}, map[string]any{"type": "integer", "minimum": 0}}}, float64(-1)},
	}
	for i, tc := range tests {
		if len(validateAgainstSchema(oa, "fixture", "negative", tc.schema, tc.value)) == 0 {
			t.Fatalf("negative %d accepted", i)
		}
	}
	if errs := validateAgainstSchema(oa, "fixture", "unicode", map[string]any{"type": "string", "maxLength": 2}, "аб"); len(errs) > 0 {
		t.Fatal(errs)
	}
}

func TestPersistenceLagAtResponseAndVisibleLoss(t *testing.T) {
	srv := contractTestServer()
	srv.ps = &collectors.PersistenceState{}
	srv.ps.LastSuccessUnix.Store(time.Now().Add(-12 * time.Second).Unix())
	srv.ps.LagSeconds.Store(0)
	srv.ps.DataLoss.Store(true)
	_, body := doGet(t, srv.Handler(), "/api/v1/health")
	health := body["data"].(map[string]any)
	if health["persistenceLagSeconds"].(float64) < 12 || health["dataLoss"] != true {
		t.Fatal("lag frozen or loss hidden")
	}
	_, body = doGet(t, srv.Handler(), "/api/v1/summary")
	summary := body["data"].(map[string]any)
	if summary["overall"] == "healthy" || len(summary["alerts"].([]any)) == 0 {
		t.Fatal("overview hides incomplete persistence")
	}
}
