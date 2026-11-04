#!/usr/bin/env python3
"""Offline tests for release/seed template qualification (static scope only)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import release_qualification as rq  # noqa: E402


class TestQualification(unittest.TestCase):
    def test_templates_parse_and_qualify(self):
        release = rq.parse_template(HERE / "p8c-portal-release.yml.template")
        seed = rq.parse_template(HERE / "p8c-portal-seed.yml.template")
        errs = rq.checks(release, seed)
        self.assertEqual(errs, [], errs)

    def test_on_not_coerced_to_bool(self):
        release = rq.parse_template(HERE / "p8c-portal-release.yml.template")
        # `on` must remain a string key, not YAML 1.1 boolean True.
        self.assertIn("on", release)
        self.assertNotIn(True, release)

    def test_seed_not_release(self):
        seed_text = (HERE / "p8c-portal-seed.yml.template").read_text()
        self.assertIn("bootstrap-seed", seed_text)
        self.assertNotIn("p8c-portal-release", seed_text.split("name:")[-1][:40])


if __name__ == "__main__":
    unittest.main(verbosity=2)
