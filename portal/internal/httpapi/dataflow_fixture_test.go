package httpapi

import (
	"encoding/json"
	"github.com/dedvmedved-dot/otus-diplom/portal/internal/collectors"
	"os"
	"path/filepath"
	"testing"
)

func TestExportActualCollectorHandlerResponses(t *testing.T) {
	dir := os.Getenv("PORTAL_FIXTURE_DIR")
	if dir == "" {
		t.Skip("run tools/test-dataflow.sh")
	}
	b, err := os.ReadFile(filepath.Join(dir, "collector-snapshot.json"))
	if err != nil {
		t.Fatal(err)
	}
	var snap collectors.Snapshot
	if err = json.Unmarshal(b, &snap); err != nil {
		t.Fatal(err)
	}
	srv := contractTestServer()
	srv.collector = mockSnapshotProvider{&snap}
	srv.store = failStore{}
	oa := loadOpenAPI(t)
	responses := map[string]any{}
	for path := range srv.apiRoutes() {
		code, body := doGet(t, srv.Handler(), path)
		if code != 200 {
			t.Fatal(code)
		}
		for _, err := range validateAgainstSchema(oa, path, "collector response", schemaFor(t, oa, path), body) {
			t.Error(err)
		}
		responses[path] = body
	}
	b, err = json.Marshal(responses)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(dir, "api-responses.json"), b, 0600); err != nil {
		t.Fatal(err)
	}
}
