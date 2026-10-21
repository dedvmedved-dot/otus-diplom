package httpapi

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
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

// validateAgainstSchema collects violations (returns them instead of failing).
// Supports: $ref, object/array/string/integer/number/boolean types, required,
// enum, additionalProperties:false, nullable, anyOf, and integer min/max.
func validateAgainstSchema(oa map[string]any, path, name string, schema map[string]any, val any) []error {
	var errs []error
	if schema == nil {
		return errs
	}
	if ref, ok := schema["$ref"].(string); ok {
		if strings.HasPrefix(ref, "#/components/schemas/") {
			comp := strings.TrimPrefix(ref, "#/components/schemas/")
			if cs, ok := oa["components"].(map[string]any)["schemas"].(map[string]any)[comp].(map[string]any); ok {
				return validateAgainstSchema(oa, path, name, cs, val)
			}
		}
		return errs
	}
	// nullable: null value is valid when nullable:true, type:"null", or no type.
	if val == nil {
		if n, ok := schema["nullable"].(bool); ok && n {
			return errs
		}
		if t, _ := schema["type"].(string); t == "null" {
			return errs
		}
		if _, hasType := schema["type"]; !hasType {
			return errs
		}
		errs = append(errs, fmt.Errorf("%s %s: null not allowed", path, name))
		return errs
	}
	// type:"null" requires a null value.
	if t, _ := schema["type"].(string); t == "null" {
		errs = append(errs, fmt.Errorf("%s %s: expected null, got %v", path, name, val))
		return errs
	}
	// anyOf: value must match at least one branch.
	if branches, ok := schema["anyOf"].([]any); ok {
		for _, b := range branches {
			bs, _ := b.(map[string]any)
			if len(validateAgainstSchema(oa, path, name, bs, val)) == 0 {
				return nil
			}
		}
		errs = append(errs, fmt.Errorf("%s %s: value %v matches no anyOf branch", path, name, val))
		return errs
	}
	st, _ := schema["type"].(string)
	switch st {
	case "object":
		obj, ok := val.(map[string]any)
		if !ok {
			errs = append(errs, fmt.Errorf("%s %s: expected object, got %T", path, name, val))
			return errs
		}
		props, _ := schema["properties"].(map[string]any)
		requiredSet := map[string]bool{}
		if req, ok := schema["required"].([]any); ok {
			for _, r := range req {
				requiredSet[r.(string)] = true
			}
		}
		for rk := range requiredSet {
			if _, ok := obj[rk]; !ok {
				errs = append(errs, fmt.Errorf("%s %s: missing required field %q", path, name, rk))
			}
		}
		if ap, ok := schema["additionalProperties"].(bool); ok && !ap {
			for k := range obj {
				if _, known := props[k]; !known {
					errs = append(errs, fmt.Errorf("%s %s: additionalProperties=false but field %q present", path, name, k))
				}
			}
		}
		for k, ps := range props {
			if v, ok := obj[k]; ok {
				errs = append(errs, validateAgainstSchema(oa, path, name+"."+k, ps.(map[string]any), v)...)
			}
		}
	case "array":
		arr, ok := val.([]any)
		if !ok {
			errs = append(errs, fmt.Errorf("%s %s: expected array, got %T", path, name, val))
			return errs
		}
		if is, ok := schema["items"].(map[string]any); ok {
			for i, item := range arr {
				errs = append(errs, validateAgainstSchema(oa, path, fmt.Sprintf("%s[%d]", name, i), is, item)...)
			}
		}
	case "string":
		if _, ok := val.(string); !ok {
			errs = append(errs, fmt.Errorf("%s %s: expected string, got %T", path, name, val))
		}
	case "integer":
		f, ok := val.(float64)
		if !ok || f != float64(int64(f)) {
			errs = append(errs, fmt.Errorf("%s %s: expected integer, got %v", path, name, val))
			return errs
		}
		if min, ok := schema["minimum"].(float64); ok && f < min {
			errs = append(errs, fmt.Errorf("%s %s: %v < minimum %v", path, name, f, min))
		}
		if max, ok := schema["maximum"].(float64); ok && f > max {
			errs = append(errs, fmt.Errorf("%s %s: %v > maximum %v", path, name, f, max))
		}
	case "number":
		if _, ok := val.(float64); !ok {
			errs = append(errs, fmt.Errorf("%s %s: expected number, got %T", path, name, val))
		}
	case "boolean":
		if _, ok := val.(bool); !ok {
			errs = append(errs, fmt.Errorf("%s %s: expected boolean, got %T", path, name, val))
		}
	default:
		// schema without a concrete type (e.g. oneOf/allOf-only) — best effort.
	}
	if enum, ok := schema["enum"].([]any); ok {
		found := false
		for _, e := range enum {
			if reflectJSON(e, val) {
				found = true
				break
			}
		}
		if !found {
			errs = append(errs, fmt.Errorf("%s %s: value %v not in enum %v", path, name, val, enum))
		}
	}
	return errs
}

func reflectJSON(a, b any) bool {
	aj, _ := json.Marshal(a)
	bj, _ := json.Marshal(b)
	return string(aj) == string(bj)
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
