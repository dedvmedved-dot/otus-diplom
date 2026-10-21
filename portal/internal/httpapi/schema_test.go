package httpapi

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// openapiJSON loads the approved OpenAPI contract (relative to this package).
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

// validateAgainstSchema checks required fields, types, enums, and
// additionalProperties:false for a single JSON value against an OpenAPI schema.
func validateAgainstSchema(t *testing.T, oa map[string]any, path, name string, schema map[string]any, val any) {
	t.Helper()
	if schema == nil {
		return
	}
	// Resolve $ref to a component schema.
	if ref, ok := schema["$ref"].(string); ok {
		if strings.HasPrefix(ref, "#/components/schemas/") {
			comp := strings.TrimPrefix(ref, "#/components/schemas/")
			if cs, ok := oa["components"].(map[string]any)["schemas"].(map[string]any)[comp].(map[string]any); ok {
				validateAgainstSchema(t, oa, path, name, cs, val)
			}
		}
		return
	}
	switch st := schema["type"].(type) {
	case string:
		switch st {
		case "object":
			obj, ok := val.(map[string]any)
			if !ok {
				t.Errorf("%s %s: expected object, got %T", path, name, val)
				return
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
					t.Errorf("%s %s: missing required field %q", path, name, rk)
				}
			}
			if ap, ok := schema["additionalProperties"].(bool); ok && !ap {
				for k := range obj {
					if _, known := props[k]; !known {
						t.Errorf("%s %s: additionalProperties=false but field %q present", path, name, k)
					}
				}
			}
			for k, ps := range props {
				if v, ok := obj[k]; ok {
					validateAgainstSchema(t, oa, path, name+"."+k, ps.(map[string]any), v)
				}
			}
		case "array":
			arr, ok := val.([]any)
			if !ok {
				t.Errorf("%s %s: expected array, got %T", path, name, val)
				return
			}
			for i, item := range arr {
				if is, ok := schema["items"].(map[string]any); ok {
					validateAgainstSchema(t, oa, path, name, is, item)
				}
				_ = i
			}
		case "string":
			if _, ok := val.(string); !ok {
				t.Errorf("%s %s: expected string, got %T", path, name, val)
			}
		case "integer":
			if _, ok := val.(float64); !ok {
				t.Errorf("%s %s: expected integer, got %T", path, name, val)
			}
		case "boolean":
			if _, ok := val.(bool); !ok {
				t.Errorf("%s %s: expected boolean, got %T", path, name, val)
			}
		case "number":
			if _, ok := val.(float64); !ok {
				t.Errorf("%s %s: expected number, got %T", path, name, val)
			}
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
				t.Errorf("%s %s: value %v not in enum %v", path, name, val, enum)
			}
		}
	}
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
		validateAgainstSchema(t, oa, p, "response", schema, body)
	}
}

func TestSchemaDrivenErrorResponses(t *testing.T) {
	oa := loadOpenAPI(t)
	srv := contractTestServer()
	h := srv.Handler()

	// 404 unknown path
	req := httptest.NewRequest(http.MethodGet, "/api/v1/does-not-exist", nil)
	req.SetBasicAuth("portal-operator", "test-password")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	var body map[string]any
	json.Unmarshal(rr.Body.Bytes(), &body)
	for _, k := range []string{"requestId", "generatedAt", "code", "message"} {
		if _, ok := body[k]; !ok {
			t.Fatalf("error missing %q", k)
		}
	}
	if body["code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND, got %v", body["code"])
	}
	_ = oa
	_ = strings.TrimSpace
}
