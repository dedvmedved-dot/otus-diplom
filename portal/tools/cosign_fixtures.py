#!/usr/bin/env python3
"""Shared OFFLINE fixtures for the private Sigstore keyless trust chain.

These fixtures are used by the gate's ``verify_keyless_trust_config`` (via
``test_owner_gate_barrier.py``) and by the offline loader-acceptance test
(``test_cosign_cli_flags.py``) that drives the REAL cosign v3.1.3 binary with
actual parameters (not ``--help``).

The trusted root and signing config are structurally valid Sigstore artifacts
(the exact protobuf-JSON shapes ``root.NewTrustedRootFromPath`` /
``root.NewSigningConfigFromPath`` accept) bound to the PRIVATE approved origins.
The crypto material (tlog public key + CA certificate) is a locally-generated
EC P-256 key and self-signed certificate — real DER bytes, because cosign
v3.1.3's trusted-root loader actually parses the tlog public key (a fake byte
string is rejected with ``failed to parse public key for tlog``).

No network access; everything is generated locally and embedded.
"""
from __future__ import annotations

import base64

# Approved PRIVATE origins. These are Owner-supplied P0 values; the OIDC issuer
# is the source-confirmed Forgejo Actions issuer (never guessed). The gate
# requires the signed config/root to point at EXACTLY these, so a foreign HTTPS
# origin is refused even when the material digest matches the pin.
APPROVED_FULCIO_URL = "https://fulcio.private.example"
APPROVED_REKOR_URL = "https://rekor.private.example"
APPROVED_OIDC_ISSUER = "https://git.aiopslab.online/api/actions"

SIGNING_CONFIG_MEDIA_TYPE = "application/vnd.dev.sigstore.signingconfig.v0.2+json"
TRUSTED_ROOT_MEDIA_TYPE = "application/vnd.dev.sigstore.trustedroot+json;version=0.1"

# Locally-generated EC P-256 material (offline). The tlog public key is a PKIX
# SubjectPublicKeyInfo DER; the CA certificate is a self-signed X.509 DER.
_TLOG_PUBKEY_B64 = (
    "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEm6yftyAJfkUAsFWD2LlehnVL8ndo"
    "Iv62Zke2jsR9aTX5X/t/PxYi7+tMgpOpM1Ag0qigCX6gzqUQ5Han7Ie2zA=="
)
_CA_CERT_B64 = (
    "MIIBvTCCAWOgAwIBAgIUA4mu9P0Dyf9AyFiEgrAvmTe889kwCgYIKoZIzj0EAwIw"
    "NDEYMBYGA1UEAwwPcHJpdmF0ZS5leGFtcGxlMRgwFgYDVQQKDA9wcml2YXRlLmV4"
    "YW1wbGUwHhcNMjYxMTI4MTUyMDUxWhcNMzYxMTI1MTUyMDUxWjA0MRgwFgYDVQQD"
    "DA9wcml2YXRlLmV4YW1wbGUxGDAWBgNVBAoMD3ByaXZhdGUuZXhhbXBsZTBZMBMG"
    "ByqGSM49AgEGCCqGSM49AwEHA0IABJusn7cgCX5FALBVg9i5XoZ1S/J3aCL+tmZH"
    "to7EfWk1+V/7fz8WIu/rTIKTqTNQINKooAl+oM6lEOR2p+yHtsyjUzBRMB0GA1Ud"
    "DgQWBBTOabdZNUsAJ8O29oW7OnqwYp6o3zAfBgNVHSMEGDAWgBTOabdZNUsAJ8O2"
    "9oW7OnqwYp6o3zAPBgNVHRMBAf8EBTADAQH/MAoGCCqGSM49BAMCA0gAMEUCIACk"
    "7dJhzJYlDPOy/sItvlhbAsao3cK6suCcbHmjsbpuAiEAzR4hW3N67qSZE4A6p13H"
    "AYOti+DaQQR2/1f/ZJKN3yI="
)
_LOG_ID_B64 = base64.b64encode(b"01234567890123456789012345678901").decode()


def make_signing_config(fulcio_url=APPROVED_FULCIO_URL, rekor_url=APPROVED_REKOR_URL,
                        oidc_issuer=APPROVED_OIDC_ISSUER):
    """A coherent signing_config.v0.2 bound to the given (default: private) origins.

    No ADDITIONAL service (review #172 item 1): ``tsaUrls`` is absent and
    ``tsaConfig`` is the empty selector ``{}`` (the canonical "no TSA" shape),
    because the private chain approves ONLY Fulcio / OIDC / Rekor."""
    return {
        "mediaType": SIGNING_CONFIG_MEDIA_TYPE,
        "caUrls": [{"url": fulcio_url, "majorApiVersion": 1,
                    "validFor": {"start": "2026-01-01T00:00:00.000Z"}}],
        "oidcUrls": [{"url": oidc_issuer, "majorApiVersion": 1,
                      "validFor": {"start": "2026-01-01T00:00:00.000Z"}}],
        "rekorTlogUrls": [{"url": rekor_url, "majorApiVersion": 1,
                           "validFor": {"start": "2026-01-01T00:00:00.000Z"}}],
        "rekorTlogConfig": {"selector": "ANY"},
        "tsaConfig": {},
    }


def make_trusted_root(fulcio_url=APPROVED_FULCIO_URL, rekor_url=APPROVED_REKOR_URL):
    """A structurally-valid, USABLE Sigstore trusted root (one tlog + one CA with
    a real cert chain) bound to the given (default: private) origins."""
    return {
        "mediaType": TRUSTED_ROOT_MEDIA_TYPE,
        "tlogs": [{
            "baseUrl": rekor_url,
            "hashAlgorithm": "SHA2_256",
            "publicKey": {"rawBytes": _TLOG_PUBKEY_B64,
                          "keyDetails": "PKIX_ECDSA_P256_SHA_256",
                          "validFor": {"start": "2026-01-01T00:00:00Z"}},
            "logId": {"keyId": _LOG_ID_B64},
        }],
        "certificateAuthorities": [{
            "subject": {"organization": "private.example", "commonName": "private.example"},
            "uri": fulcio_url,
            "certChain": {"certificates": [{"rawBytes": _CA_CERT_B64}]},
            "validFor": {"start": "2026-01-01T00:00:00Z",
                         "end": "2036-01-01T00:00:00Z"},
        }],
        "ctlogs": [],
        "timestampAuthorities": [],
    }
