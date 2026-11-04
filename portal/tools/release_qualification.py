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
    release_text = Path(HERE / "p8c-portal-release.yml.template").read_text()
    # R-01: dispatch-only, exact repo/ref
    if not re.search(r"^on:\s*$[\s\S]*?workflow_dispatch", release_text, re.M):
        errs.append("release on: must be workflow_dispatch only")
    if "dedvmedved-dot/otus-diplom" not in release_text or "refs/heads/main" not in release_text:
        errs.append("release must pin repository + refs/heads/main")
    # R-03: permissions
    jobs = release.get("jobs", {})
    if jobs.get("test", {}).get("permissions", {"contents": "read"}) != {"contents": "read"}:
        errs.append("test permissions must be contents:read")
    rp = jobs.get("release", {}).get("permissions", {})
    if rp.get("contents") != "read" or rp.get("packages") != "write" or rp.get("id-token") != "write":
        errs.append("release permissions must be contents:read + packages:write + id-token:write")
    # R-02: timeouts
    if jobs.get("test", {}).get("timeout-minutes") != 20:
        errs.append("test timeout-minutes must be 20")
    if jobs.get("release", {}).get("timeout-minutes") != 30:
        errs.append("release timeout-minutes must be 30")
    # R-01: immutable checkout + persist-credentials:false
    checkout = None
    for j in jobs.values():
        for s in j.get("steps", []):
            if isinstance(s, dict) and s.get("uses", "").startswith("actions/checkout@"):
                checkout = s
    if checkout is None or checkout.get("with", {}).get("persist-credentials") is not False:
        errs.append("checkout must use immutable SHA + persist-credentials:false")
    # R-03: no deploy/SSH/kubectl/production mutation steps
    for j in jobs.values():
        for s in j.get("steps", []):
            run = s.get("run", "") if isinstance(s, dict) else ""
            for banned in ("kubectl", "ssh ", "apply -f", "production"):
                if banned in run:
                    errs.append(f"forbidden step content in template: {banned}")
    # seed requirements
    seed_text = Path(HERE / "p8c-portal-seed.yml.template").read_text()
    if "ghcr.io/dedvmedved-dot/otus-diplom-portal" not in seed_text:
        errs.append("seed template missing exact target package")
    if "not-deployable" not in seed_text and "not deployable" not in seed_text:
        errs.append("seed template missing not-deployable marking")
    if "release-check.py private" not in seed_text:
        errs.append("seed template missing private precondition")
    if "packages: write" not in seed_text:
        errs.append("seed template missing packages:write")
    return errs


def main():
    release = parse_template(HERE / "p8c-portal-release.yml.template")
    seed = parse_template(HERE / "p8c-portal-seed.yml.template")
    errs = checks(release, seed)
    print(json.dumps({"errors": errs, "qualified": not errs}, sort_keys=True))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
