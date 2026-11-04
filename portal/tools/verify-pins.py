#!/usr/bin/env python3
"""Offline-public supply-chain pin verification.

Downloads each pinned binary from its official upstream HTTPS endpoint into an
isolated task cache, computes sha256 over the exact bytes, and compares against
the declared checksum. Action refs are verified as existing commits in the
upstream repo; the postgres image digest is verified via the anonymous public
Docker Hub bearer flow. This is public-source verification only; it never
touches PAK/SSH/GHCR-private packages or credentials.

Result: VERIFIED | MISMATCH | UNAVAILABLE per pin.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

LOCK = os.path.join(os.path.dirname(__file__), "pins.lock.json")
CACHE = os.environ.get("P8C_PIN_CACHE", "/tmp/p8c-pin-cache")

UA = "p8c-pin-verify/1.0 (+https://github.com/dedvmedved-dot/otus-diplom)"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        raise RuntimeError("redirect forbidden")


def http_get_follow(url, headers=None, timeout=60, cap=64 * 1024 * 1024):
    # Public binary downloads follow official CDN redirects (e.g. GitHub -> objects.githubusercontent.com);
    # the final resolved source is recorded for provenance.
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        final = resp.geturl()
        body = resp.read(cap + 1)
        if len(body) > cap:
            raise RuntimeError("response exceeds cap")
        return body, final, resp.status


def http_get(url, headers=None, timeout=60, cap=64 * 1024 * 1024):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
    opener = urllib.request.build_opener(NoRedirect)
    with opener.open(req, timeout=timeout) as resp:
        final = resp.geturl()
        body = resp.read(cap + 1)
        if len(body) > cap:
            raise RuntimeError("response exceeds cap")
        return body, final, resp.status


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def sanitize_url(url):
    # Strip query/fragment/userinfo; keep scheme+host+path only (no signed CDN params persisted).
    import urllib.parse as up
    p = up.urlsplit(url)
    return up.urlunsplit((p.scheme, p.hostname or "", p.path, "", ""))


def verify_binary(pin):
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, pin["id"] + ".dl")
    try:
        body, final, status = http_get_follow(pin["url"], cap=512 * 1024 * 1024)
        actual = sha256(body)
        open(dest, "wb").write(body)
        if status != 200:
            return {"id": pin["id"], "status": "UNAVAILABLE", "http": status, "final_url": sanitize_url(final), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        verdict = "VERIFIED" if actual == pin["sha256"] else "MISMATCH"
        return {"id": pin["id"], "status": verdict, "declared": pin["sha256"], "actual": actual, "bytes": len(body), "final_url": sanitize_url(final), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    except Exception as e:
        return {"id": pin["id"], "status": "UNAVAILABLE", "error": type(e).__name__ + ": " + str(e)[:200], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def verify_action(pin):
    url = f"https://api.github.com/repos/{pin['repo']}/git/commits/{pin['sha']}"
    try:
        body, final, status = http_get(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"}, cap=1024 * 1024)
        if status == 200:
            c = json.loads(body)
            verdict = "VERIFIED" if c.get("sha") == pin["sha"] else "MISMATCH"
            return {"id": pin["id"], "status": verdict, "commit_sha": c.get("sha"), "tag_annotation_not_authoritative": pin["tag_annotation"]}
        return {"id": pin["id"], "status": "UNAVAILABLE", "http": status}
    except Exception as e:
        return {"id": pin["id"], "status": "UNAVAILABLE", "error": type(e).__name__ + ": " + str(e)[:200]}


def verify_image(pin):
    # Anonymous public Docker Hub bearer flow: token -> manifest by digest.
    ref = pin["ref"]
    try:
        body, _, status = http_get(f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/postgres:pull", cap=64 * 1024)
        token = json.loads(body).get("token")
        hdr = {"Authorization": "Bearer " + token, "Accept": "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json"}
        mbody, _, mstatus = http_get(f"https://registry-1.docker.io/v2/library/postgres/manifests/{pin['digest']}", headers=hdr, cap=8 * 1024 * 1024)
        actual = "sha256:" + sha256(mbody)
        verdict = "VERIFIED" if (actual == pin["digest"] and mstatus == 200) else ("MISMATCH" if mstatus == 200 else "UNAVAILABLE")
        return {"id": pin["id"], "status": verdict, "ref": ref, "declared": pin["digest"], "manifest_sha256": actual, "http": mstatus}
    except Exception as e:
        return {"id": pin["id"], "status": "UNAVAILABLE", "error": type(e).__name__ + ": " + str(e)[:200]}


def main():
    lock = json.load(open(LOCK))
    results = []
    for p in lock["binaries"]:
        results.append(verify_binary(p))
    for p in lock["actions"]:
        results.append(verify_action(p))
    for p in lock["images"]:
        results.append(verify_image(p))
    out = {"source_sha": "RECORDED_AT_COMMIT", "results": results}
    json.dump(out, open(os.path.join(CACHE, "pin-verification.json"), "w"), indent=2)
    for r in results:
        print(f"{r['id']:14} {r['status']}")
    print("cache:", CACHE)
    # explicit aggregate failure: any non-VERIFIED => nonzero exit
    return 0 if all(r["status"] == "VERIFIED" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
