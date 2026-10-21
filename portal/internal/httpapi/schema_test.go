package httpapi

import (
	"encoding/json"
	"fmt"
	"github.com/santhosh-tekuri/jsonschema/v6"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func loadOpenAPI(t *testing.T) map[string]any {
	t.Helper()
	p := filepath.Join("..", "..", "..", "docs", "architecture", "p8c", "openapi.json")
	b, err := os.ReadFile(p)
	if err != nil {
		t.Fatalf("read openapi: %v", err)
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		t.Fatalf("parse openapi: %v", err)
	}
	return m
}

func schemaFor(t *testing.T, oa map[string]any, path string) map[string]any {
	t.Helper()
	paths := oa["paths"].(map[string]any)
	item := paths[path].(map[string]any)
	get := item["get"].(map[string]any)
	resp := get["responses"].(map[string]any)["200"].(map[string]any)
	content := resp["content"].(map[string]any)["application/json"].(map[string]any)
	return content["schema"].(map[string]any)
}

// The approved OpenAPI 3.1 schemas are JSON Schema 2020-12. Use a pinned
// standards implementation with format assertions, not a handwritten subset.
type rejectExternalSchema struct{}

func (rejectExternalSchema) Load(url string) (any, error) {
	return nil, fmt.Errorf("external schema forbidden: %s", url)
}
func validateAgainstSchema(oa map[string]any, path, name string, schema map[string]any, val any) []error {
	c := jsonschema.NewCompiler()
	c.DefaultDraft(jsonschema.Draft2020)
	c.AssertFormat()
	c.UseLoader(rejectExternalSchema{})
	doc := map[string]any{"$schema": "https://json-schema.org/draft/2020-12/schema", "components": oa["components"], "response": schema}
	if err := c.AddResource("https://portal.invalid/contract", doc); err != nil {
		return []error{err}
	}
	compiled, err := c.Compile("https://portal.invalid/contract#/response")
	if err != nil {
		return []error{err}
	}
	if err := compiled.Validate(val); err != nil {
		return []error{fmt.Errorf("%s %s: %w", path, name, err)}
	}
	return nil
}

func TestSchemaDrivenHandlerResponses(t *testing.T) {
	oa := loadOpenAPI(t)
	srv := contractTestServer()
	h := srv.Handler()
	endpoints := []string{
		"/api/v1/health", "/api/v1/summary", "/api/v1/nodes", "/api/v1/workloads",
		"/api/v1/pods", "/api/v1/services", "/api/v1/storage", "/api/v1/backups",
		"/api/v1/database", "/api/v1/metrics", "/api/v1/events",
	}
	for _, p := range endpoints {
		req := httptest.NewRequest(http.MethodGet, p, nil)
		req.SetBasicAuth("portal-operator", "test-password")
		rr := httptest.NewRecorder()
		h.ServeHTTP(rr, req)
		if rr.Code != http.StatusOK {
			t.Fatalf("%s: expected 200, got %d", p, rr.Code)
		}
		var body map[string]any
		if err := json.Unmarshal(rr.Body.Bytes(), &body); err != nil {
			t.Fatalf("%s: bad JSON: %v", p, err)
		}
		schema := schemaFor(t, oa, p)
		for _, err := range validateAgainstSchema(oa, p, "response", schema, body) {
			t.Errorf("%v", err)
		}
	}
}

func TestSchemaValidatorRejectsBadResponses(t *testing.T) {
	oa := loadOpenAPI(t)
	// A deliberately malformed nodes response: wrong type for items + an
	// additional field violating additionalProperties:false.
	bad := map[string]any{
		"requestId": "x", "generatedAt": "2026-10-21T00:00:00Z", "observedAt": nil,
		"freshness": "fresh", "partial": false, "sources": []any{}, "warnings": []any{}, "nextCursor": nil,
		"data": map[string]any{"items": "not-an-array", "bogusField": true},
	}
	schema := schemaFor(t, oa, "/api/v1/nodes")
	errs := validateAgainstSchema(oa, "/api/v1/nodes", "response", schema, bad)
	if len(errs) == 0 {
		t.Fatal("expected validator to reject malformed response")
	}

	// A null data object must be rejected (data is a required object, not nullable).
	nullData := map[string]any{
		"requestId": "x", "generatedAt": "2026-10-21T00:00:00Z", "observedAt": "2026-10-21T00:00:00Z",
		"freshness": "fresh", "partial": false, "sources": []any{}, "warnings": []any{}, "nextCursor": nil,
		"data": nil,
	}
	if errs := validateAgainstSchema(oa, "/api/v1/nodes", "response", schema, nullData); len(errs) == 0 {
		t.Fatal("expected validator to reject null data")
	}

	// A valid envelope (empty items) must pass.
	good := map[string]any{
		"requestId": "x", "generatedAt": "2026-10-21T00:00:00Z", "observedAt": "2026-10-21T00:00:00Z",
		"freshness": "fresh", "partial": false, "sources": []any{}, "warnings": []any{}, "nextCursor": nil,
		"data": map[string]any{"items": []any{}},
	}
	if errs := validateAgainstSchema(oa, "/api/v1/nodes", "response", schema, good); len(errs) != 0 {
		t.Fatalf("expected valid response to pass, got %v", errs)
	}
}
