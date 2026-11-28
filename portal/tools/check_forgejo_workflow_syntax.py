#!/usr/bin/env python3
"""Offline syntax/structure check for the INACTIVE Forgejo workflow template.

Validates portal/tools/p8c-portal-forgejo-release.yml.template without running
CI: YAML well-formedness, top-level structure (name / on / jobs), per-job
runs-on+steps, and balanced ${{ }} expressions. Prints a compact verdict and
exits 0 only when all checks pass.

NOTE on the `on:` key: PyYAML (YAML 1.1) coerces the bare key `on` to boolean
True. This script therefore accepts the trigger key as either the string "on"
or the boolean True and reports which form it saw; Forgejo's YAML parser reads
the key as `on` (trigger). This is a known PyYAML-1.1 quirk, not a workflow defect.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

TEMPLATE = Path(__file__).parent / "p8c-portal-forgejo-release.yml.template"
EXPR = re.compile(r"\$\{\{(.*?)\}\}", re.DOTALL)


def check_balanced(text):
    opens = text.count("${{")
    closes = text.count("}}")
    if opens != closes:
        return False, "unbalanced ${{ }}: %d open vs %d close" % (opens, closes)
    return True, "%d expressions balanced" % opens


def main():
    errors = []
    text = TEMPLATE.read_text()
    try:
        doc = yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001
        print("YAML PARSE ERROR: %s" % exc)
        return 1
    if not isinstance(doc, dict):
        print("STRUCTURE ERROR: top level is not a mapping")
        return 1

    # trigger key: `on` (string) or True (PyYAML 1.1 coercion of bare `on`)
    has_on = "on" in doc or True in doc
    has_name = isinstance(doc.get("name"), str)
    jobs = doc.get("jobs")
    print("name:", doc.get("name"))
    trigger = "on" if "on" in doc else ("True(bool; PyYAML 1.1 coercion of bare `on`)" if has_on else "MISSING")
    print("trigger key:", trigger)
    if not has_on:
        errors.append("missing trigger key `on`")
    if not has_name:
        errors.append("missing string `name`")
    if not isinstance(jobs, dict) or not jobs:
        errors.append("missing/non-mapping `jobs`")
    else:
        print("jobs (%d): %s" % (len(jobs), ", ".join(jobs)))
        for jname, job in jobs.items():
            if not isinstance(job, dict):
                errors.append("job %r is not a mapping" % jname)
                continue
            if "runs-on" not in job:
                errors.append("job %r missing runs-on" % jname)
            steps = job.get("steps")
            if not isinstance(steps, list) or not steps:
                errors.append("job %r missing/non-list steps" % jname)
            else:
                print("  - %s: runs-on=%r, %d steps" % (jname, job.get("runs-on"), len(steps)))

    ok, msg = check_balanced(text)
    print(msg)
    if not ok:
        errors.append(msg)

    if errors:
        for e in errors:
            print("ERROR:", e)
        print("SYNTAX = FAIL")
        return 1
    print("SYNTAX = VERIFIED (YAML well-formed; structure + expressions OK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
