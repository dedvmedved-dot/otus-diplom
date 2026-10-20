package httpapi

import (
	"net/http/httptest"
	"testing"
)

func TestParseListQueryDefaults(t *testing.T) {
	r := httptest.NewRequest("GET", "/api/v1/nodes", nil)
	limit, offset, ns, err := parseListQuery(r)
	if err != nil || limit != 50 || offset != 0 || ns != "" {
		t.Fatalf("got limit=%d offset=%d ns=%q err=%v", limit, offset, ns, err)
	}
}

func TestParseListQueryLimit(t *testing.T) {
	r := httptest.NewRequest("GET", "/api/v1/nodes?limit=10", nil)
	limit, _, _, err := parseListQuery(r)
	if err != nil || limit != 10 {
		t.Fatalf("got limit=%d err=%v", limit, err)
	}
}

func TestParseListQueryInvalidLimit(t *testing.T) {
	r := httptest.NewRequest("GET", "/api/v1/nodes?limit=999", nil)
	if _, _, _, err := parseListQuery(r); err == nil {
		t.Fatal("expected error for limit out of range")
	}
}

func TestParseListQueryInvalidNamespace(t *testing.T) {
	r := httptest.NewRequest("GET", "/api/v1/pods?namespace=Bad_Name!", nil)
	if _, _, _, err := parseListQuery(r); err == nil {
		t.Fatal("expected error for invalid namespace")
	}
}

func TestPaginate(t *testing.T) {
	items := []string{"a", "b", "c", "d", "e"}
	page, next := paginate(items, 2, 0)
	if len(page) != 2 || page[0] != "a" || page[1] != "b" {
		t.Fatal("first page wrong")
	}
	if next == nil {
		t.Fatal("expected next cursor")
	}
	page2, next2 := paginate(items, 2, 4)
	if len(page2) != 1 || page2[0] != "e" {
		t.Fatal("last page wrong")
	}
	if next2 != nil {
		t.Fatal("expected nil next cursor at end")
	}
}

func TestPaginateExpiredCursor(t *testing.T) {
	items := []string{"a", "b"}
	page, _ := paginate(items, 2, 100)
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
