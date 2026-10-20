package httpapi

import (
	"net/http/httptest"
	"testing"
)

func testServer() *Server { return &Server{} }

func TestParseListQueryDefaults(t *testing.T) {
	s := testServer()
	r := httptest.NewRequest("GET", "/api/v1/nodes", nil)
	limit, offset, ns, err := s.parseListQuery(r, []string{"limit", "cursor"}, "nodes")
	if err != nil || limit != 50 || offset != 0 || ns != "" {
		t.Fatalf("got limit=%d offset=%d ns=%q err=%v", limit, offset, ns, err)
	}
}

func TestParseListQueryLimit(t *testing.T) {
	s := testServer()
	r := httptest.NewRequest("GET", "/api/v1/nodes?limit=10", nil)
	limit, _, _, err := s.parseListQuery(r, []string{"limit", "cursor"}, "nodes")
	if err != nil || limit != 10 {
		t.Fatalf("got limit=%d err=%v", limit, err)
	}
}

func TestParseListQueryInvalidLimit(t *testing.T) {
	s := testServer()
	r := httptest.NewRequest("GET", "/api/v1/nodes?limit=999", nil)
	if _, _, _, err := s.parseListQuery(r, []string{"limit", "cursor"}, "nodes"); err == nil {
		t.Fatal("expected error for limit out of range")
	}
}

func TestParseListQueryUnknownKey(t *testing.T) {
	s := testServer()
	r := httptest.NewRequest("GET", "/api/v1/nodes?bogus=1", nil)
	if _, _, _, err := s.parseListQuery(r, []string{"limit", "cursor"}, "nodes"); err == nil {
		t.Fatal("expected error for unknown query key")
	}
}

func TestParseListQueryInvalidNamespace(t *testing.T) {
	s := testServer()
	r := httptest.NewRequest("GET", "/api/v1/pods?namespace=Bad_Name!", nil)
	if _, _, _, err := s.parseListQuery(r, []string{"limit", "cursor", "namespace"}, "pods"); err == nil {
		t.Fatal("expected error for invalid namespace")
	}
}

func TestCursorRoundTrip(t *testing.T) {
	c := encodeCursor("123456789", "portal", "nodes", 42)
	cs, err := decodeCursor(c)
	if err != nil {
		t.Fatal(err)
	}
	if cs.snapshotID != "123456789" || cs.namespace != "portal" || cs.endpoint != "nodes" || cs.offset != 42 {
		t.Fatalf("got %+v", cs)
	}
}

func TestDecodeCursorInvalid(t *testing.T) {
	if _, err := decodeCursor("not-base64!!!"); err == nil {
		t.Fatal("expected error for invalid cursor")
	}
}

func TestPaginate(t *testing.T) {
	s := testServer()
	items := []string{"a", "b", "c", "d", "e"}
	page, next := s.paginate(items, 2, 0, "", "test")
	if len(page) != 2 || page[0] != "a" || page[1] != "b" {
		t.Fatal("first page wrong")
	}
	if next == nil {
		t.Fatal("expected next cursor")
	}
	page2, next2 := s.paginate(items, 2, 4, "", "test")
	if len(page2) != 1 || page2[0] != "e" {
		t.Fatal("last page wrong")
	}
	if next2 != nil {
		t.Fatal("expected nil next cursor at end")
	}
}

func TestPaginateExpiredCursor(t *testing.T) {
	s := testServer()
	items := []string{"a", "b"}
	page, _ := s.paginate(items, 2, 100, "", "test")
	if len(page) != 0 {
		t.Fatal("expected empty page for out-of-range offset")
	}
}

func TestDNS1123(t *testing.T) {
	for _, ok := range []string{"portal", "a-b", "a1b2"} {
		if !dns1123(ok) {
			t.Fatalf("expected %q to be valid", ok)
		}
	}
	for _, bad := range []string{"", "-a", "a-", "Bad", "a_b"} {
		if dns1123(bad) {
			t.Fatalf("expected %q to be invalid", bad)
		}
	}
}
