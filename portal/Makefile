GO ?= go
BINARY := portal
SRC_REV := $(shell git -C .. rev-parse HEAD 2>/dev/null || echo unknown)
BUILD_TIME := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS := -s -w -X main.sourceRevision=$(SRC_REV) -X main.buildTime=$(BUILD_TIME)
GOTOOLCHAIN := local

.PHONY: build test vet race image tidy verify

build:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 GOTOOLCHAIN=$(GOTOOLCHAIN) $(GO) build -trimpath -ldflags "$(LDFLAGS)" -o $(BINARY) ./cmd/portal

test:
	$(GO) test ./...

vet:
	$(GO) vet ./...

race:
	$(GO) test -race ./...

tidy:
	$(GO) mod tidy
	$(GO) mod verify

verify:
	$(GO) mod verify

image: build
	# OCI build is performed with pinned BuildKit (see supply-chain evidence).
	@echo "build $(BINARY) done; build OCI image via buildctl (see scripts/build-oci.sh)"
