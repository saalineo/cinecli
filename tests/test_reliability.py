import time
import unittest
from unittest.mock import patch

from search.searcher import enabled_sources, search
from utils.safety import dns_leak_check


class SearchReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "timeout": 1,
            "search_budget": 1,
            "sources": {
                "yts": True, "eztv": False, "tpb": False, "x1337": False,
                "solid": False, "galaxy": False, "nyaa": False, "lime": False,
                "btdig": False,
            },
        }
        self.results = [
            {
                "title": str(i), "year": 0, "quality": "1080p", "seeders": 1,
                "source": "yts", "info_hash": f"{i:040x}", "raw": str(i),
            }
            for i in range(3)
        ]

    def test_disabled_japanese_source_stays_disabled(self):
        cfg = {"sources": {"nyaa": False}}
        self.assertNotIn("nyaa", enabled_sources(cfg, "movie", "japanese"))
        self.assertFalse(cfg["sources"]["nyaa"])

    def test_max_must_be_positive(self):
        with patch("search.searcher._run_provider", return_value=("yts", self.results)):
            self.assertEqual(2, len(search("x", max_results=2, cfg=self.cfg)[0]))
            with self.assertRaises(ValueError):
                search("x", max_results=0, cfg=self.cfg)

    def test_dns_check_does_not_claim_a_verdict(self):
        verdict, detail = dns_leak_check()
        self.assertIsNone(verdict)
        self.assertEqual("not_verified", detail["status"])

    def test_slow_provider_does_not_outlive_search_budget(self):
        def slow_provider(*args, **kwargs):
            time.sleep(5)
            return "yts", []

        cfg = dict(self.cfg, search_budget=1)
        started = time.monotonic()
        with patch("search.searcher._run_provider", side_effect=slow_provider):
            results, status, _ = search("x", max_results=1, cfg=cfg)
        self.assertEqual([], results)
        self.assertEqual({}, status)
        self.assertLess(time.monotonic() - started, 1.5)

    def test_search_reports_provider_lifecycle_to_the_tui(self):
        events = []
        with patch("search.searcher._run_provider", return_value=("yts", self.results)):
            search(
                "x",
                max_results=1,
                cfg=self.cfg,
                progress=lambda source, state, count: events.append((source, state, count)),
            )
        self.assertIn(("yts", "searching", None), events)
        self.assertIn(("yts", "complete", 3), events)


if __name__ == "__main__":
    unittest.main()
