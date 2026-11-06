#!/usr/bin/env python3
"""Static source qualification for the release + seed workflow templates.

Checks that the TEMPLATE (not .github/workflows) meets the accepted R-01..R-08
and seed requirements. Static YAML/scope validation only, NOT an Actions runtime
PASS and NOT CI execution.
"""
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).parent


class _Loader(yaml.SafeLoader):
    pass


# YAML 1.1 coerces `on` to bool; treat only true/false as bool and keep `on`/`yes`/`no`/`off`
# as strings (YAML 1.2 core schema).
def _construct_bool(loader, node):
    value = loader.construct_scalar(node)
    if value == "true":
        return True
    if value == "false":
        return False
    return value


_Loader.add_constructor("tag:yaml.org,2002:bool", _construct_bool)


def parse_template(path):
    text = Path(path).read_text()
    try:
        return yaml.load(text, Loader=_Loader)
    except Exception as e:
        raise SystemExit(f"{path}: YAML parse failed: {e}")


def checks(release, seed):
    errs = []
    # R-01: dispatch-only trigger (parsed object, not disk text)
    on = release.get("on")
    if not isinstance(on, dict) or set(on.keys()) != {"workflow_dispatch"}:
        errs.append("on must be workflow_dispatch only")
    jobs = release.get("jobs", {})
    if "dedvmedved-dot/otus-diplom" not in str(jobs) or "refs/heads/main" not in str(jobs):
        errs.append("release must pin repository + refs/heads/main")
    # R-03: permissions (exact, no extras)
    if jobs.get("test", {}).get("permissions", {"contents": "read"}) != {"contents": "read"}:
        errs.append("test permissions must be contents:read")
    rp = jobs.get("release", {}).get("permissions", {})
    if set(rp.keys()) != {"contents", "packages", "id-token"} or rp.get("contents") != "read" \
            or rp.get("packages") != "write" or rp.get("id-token") != "write":
        errs.append("release permissions must be exactly contents:read+packages:write+id-token:write")
    # R-02: timeouts
    if jobs.get("test", {}).get("timeout-minutes") != 20:
        errs.append("test timeout-minutes must be 20")
    if jobs.get("release", {}).get("timeout-minutes") != 30:
        errs.append("release timeout-minutes must be 30")
    # R-01: immutable checkout (SHA, not mutable ref) + persist-credentials:false; at least one checkout
    saw_checkout = False
    for j in jobs.values():
        for s in j.get("steps", []):
            if isinstance(s, dict) and s.get("uses", "").startswith("actions/checkout@"):
                saw_checkout = True
                sha = s["uses"].split("@", 1)[1]
                if not re.fullmatch(r"[0-9a-f]{40}", sha):
                    errs.append("checkout must pin immutable SHA")
                if s.get("with", {}).get("persist-credentials") is not False:
                    errs.append("checkout must set persist-credentials:false")
                if s.get("with", {}).get("ref") not in (None, "${{ github.sha }}"):
                    errs.append("checkout ref must be immutable github.sha")
    if not saw_checkout:
        errs.append("release template missing checkout step")
    # top-level permissions must not be write-all (jobs must not inherit elevated scope)
    top_perm = release.get("permissions")
    if top_perm not in (None, {"contents": "read"}):
        errs.append("top-level permissions must be contents:read (no inherited write-all)")
    # R-03: no deploy/SSH/kubectl/production mutation steps
    for j in jobs.values():
        for s in j.get("steps", []):
            run = s.get("run", "") if isinstance(s, dict) else ""
            for banned in ("kubectl", "ssh ", "apply -f", "production"):
                if banned in run:
                    errs.append("forbidden step content in template: " + banned)
    # seed requirements (parsed object)
    seed_on = seed.get("on")
    if not isinstance(seed_on, dict) or set(seed_on.keys()) != {"workflow_dispatch"}:
        errs.append("seed on must be workflow_dispatch only")
    if not seed.get("jobs", {}).get("precheck"):
        errs.append("seed template missing 'precheck' job")
    seed_job = seed.get("jobs", {}).get("seed", {})
    if not seed_job:
        errs.append("seed template missing 'seed' job")
    if seed.get("permissions", {}).get("packages") != "write":
        errs.append("seed template missing packages:write")
    steps = seed_job.get("steps", [])
    priv = next((s for s in steps if isinstance(s, dict) and "private" in str(s.get("run", ""))), None)
    if priv is None:
        errs.append("seed template missing private precondition step")
    elif priv.get("env", {}).get("GITHUB_TOKEN") != "${{ secrets.GITHUB_TOKEN }}":
        errs.append("seed private step must pass GITHUB_TOKEN env")
    if not any(isinstance(s, dict) and "buildctl build" in str(s.get("run", "")) for s in steps):
        errs.append("seed template missing buildctl build route")
    if not any(isinstance(s, dict) and "Seed.Containerfile" in str(s.get("run", "")) for s in steps):
        errs.append("seed template missing Seed.Containerfile reference")
    return errs


def main():
    release = parse_template(HERE / "p8c-portal-release.yml.template")
    seed = parse_template(HERE / "p8c-portal-seed.yml.template")
    errs = checks(release, seed)
    print(json.dumps({"errors": errs, "qualified": not errs}, sort_keys=True))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
