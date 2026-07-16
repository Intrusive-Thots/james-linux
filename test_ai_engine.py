"""Tests for the enhanced AI engine: ResultStore, analysis, adaptive prompts."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from james.core.ai_engine import ResultStore, GeminiEngine


class TestResultStore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpfile = Path(self.tmpdir.name) / "memory.json"
        # Patch the MEMORY_FILE so we don't pollute real ~/.james
        self.patcher = patch.object(ResultStore, "MEMORY_FILE", self.tmpfile)
        self.patcher.start()
        self.store = ResultStore()

    def tearDown(self):
        self.patcher.stop()
        self.tmpdir.cleanup()

    def test_add_and_get_recent(self):
        self.store.add("quick_recon", "192.168.1.1", "Found 3 open ports")
        self.store.add("full_scan", "192.168.1.1", "SSH, HTTP, SMB detected")

        recent = self.store.get_recent(n=5)
        self.assertEqual(len(recent), 2)
        # Most recent first
        self.assertEqual(recent[0]["action"], "full_scan")
        self.assertEqual(recent[1]["action"], "quick_recon")

    def test_search(self):
        self.store.add("quick_recon", "192.168.1.1", "Open ports: 22, 80")
        self.store.add("osint", "example.com", "Emails harvested")
        self.store.add("full_scan", "10.0.0.1", "MySQL on 3306")

        matches = self.store.search("192.168")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["target"], "192.168.1.1")

        matches = self.store.search("example")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["action"], "osint")

    def test_get_for_target(self):
        self.store.add("scan", "target1", "result1")
        self.store.add("scan", "target2", "result2")
        self.store.add("brute", "target1", "result3")

        results = self.store.get_for_target("target1")
        self.assertEqual(len(results), 2)

    def test_ring_buffer(self):
        """Test that store doesn't grow beyond MAX_RESULTS."""
        original_max = ResultStore.MAX_RESULTS
        ResultStore.MAX_RESULTS = 5
        try:
            store = ResultStore()
            for i in range(10):
                store.add("scan", f"target{i}", f"result{i}")
            recent = store.get_recent(n=100)
            self.assertEqual(len(recent), 5)
            # Should have the last 5
            self.assertEqual(recent[0]["target"], "target9")
        finally:
            ResultStore.MAX_RESULTS = original_max

    def test_persistence(self):
        """Test save and load from disk."""
        self.store.add("scan", "192.168.1.1", "3 ports open")
        self.store.add("brute", "192.168.1.1", "SSH cracked")

        # Verify file was created
        self.assertTrue(self.tmpfile.exists())

        # Load into a new store
        store2 = ResultStore()
        recent = store2.get_recent(n=5)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["action"], "brute")

    def test_build_context_block(self):
        self.store.add("scan", "192.168.1.1", "Port 22 open, SSH")
        block = self.store.build_context_block(n=5)
        self.assertIn("RECENT RESULTS", block)
        self.assertIn("192.168.1.1", block)
        self.assertIn("scan", block)

    def test_build_context_block_empty(self):
        block = self.store.build_context_block()
        self.assertEqual(block, "")

    def test_build_knowledge_block(self):
        context = {
            "discovered_services": {
                "192.168.1.1": {
                    "ports": ["22/tcp", "80/tcp"],
                    "services": ["ssh", "http"],
                }
            },
            "scan_history": [{"target": "192.168.1.1"}],
        }
        block = self.store.build_knowledge_block(context)
        self.assertIn("DISCOVERED INFRASTRUCTURE", block)
        self.assertIn("192.168.1.1", block)
        self.assertIn("SCAN HISTORY", block)

    def test_clear(self):
        self.store.add("scan", "target", "result")
        self.store.clear()
        self.assertEqual(len(self.store.get_recent()), 0)

    def test_summary_truncation(self):
        """Summaries longer than SUMMARY_LEN are truncated."""
        long_result = "x" * 1000
        self.store.add("scan", "target", long_result)
        stored = self.store.get_recent(1)[0]
        self.assertLessEqual(len(stored["summary"]), ResultStore.SUMMARY_LEN)


class TestGeminiEngineOffline(unittest.TestCase):
    """Test GeminiEngine features that work without API key."""

    def setUp(self):
        # Ensure no API key so engine runs in offline/degraded mode
        self.orig_key = None
        import os
        if "GEMINI_API_KEY" in os.environ:
            self.orig_key = os.environ.pop("GEMINI_API_KEY")

        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmpfile = Path(self.tmpdir.name) / "memory.json"
        self.patcher = patch.object(ResultStore, "MEMORY_FILE", self.tmpfile)
        self.patcher.start()
        self.engine = GeminiEngine()

    def tearDown(self):
        self.patcher.stop()
        self.tmpdir.cleanup()
        import os
        if self.orig_key:
            os.environ["GEMINI_API_KEY"] = self.orig_key

    def test_heuristic_analysis_open_ports(self):
        result = self.engine._heuristic_analysis(
            "quick_recon",
            "22/tcp open ssh\n80/tcp open http\n445/tcp open microsoft-ds",
            {"target": "192.168.1.1"},
        )
        self.assertIsNotNone(result)
        self.assertIn("3 open port(s) found", result["findings"])
        self.assertTrue(len(result["next_steps"]) > 0)

    def test_heuristic_analysis_handshake(self):
        result = self.engine._heuristic_analysis(
            "deauth",
            "Handshake captured! File saved.",
            {"target_bssid": "AA:BB:CC", "capture_file": "/tmp/test.cap"},
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["severity"], "high")

    def test_heuristic_analysis_key_found(self):
        result = self.engine._heuristic_analysis(
            "crack_wpa",
            "KEY FOUND! Password: mysecretpass",
            {"target": "test_ap"},
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["severity"], "critical")

    def test_heuristic_analysis_no_results(self):
        result = self.engine._heuristic_analysis(
            "scan", "No hosts found", {"target": "10.0.0.1"}
        )
        self.assertIsNotNone(result)
        self.assertIn("full scan 10.0.0.1", result["next_steps"])

    def test_heuristic_analysis_clean_output(self):
        """Normal output with no significant findings returns None."""
        result = self.engine._heuristic_analysis(
            "set_context", "Context updated: target = foo", {}
        )
        self.assertIsNone(result)

    def test_phase_detection_default(self):
        phase = self.engine._detect_phase({})
        self.assertEqual(phase, "system")

    def test_phase_detection_recon(self):
        phase = self.engine._detect_phase({"target": "192.168.1.1"})
        self.assertEqual(phase, "recon")

    def test_phase_detection_wifi(self):
        phase = self.engine._detect_phase({"monitor_interface": "wlan0mon"})
        self.assertEqual(phase, "wifi")

    def test_phase_detection_web(self):
        phase = self.engine._detect_phase({"target_url": "http://example.com"})
        self.assertEqual(phase, "web")

    def test_phase_detection_cracking(self):
        phase = self.engine._detect_phase({"capture_file": "/tmp/test.cap"})
        self.assertEqual(phase, "cracking")

    def test_phase_detection_post_exploit(self):
        phase = self.engine._detect_phase({"cracked_keys": {"AA:BB": "pass"}})
        self.assertEqual(phase, "post-exploit")

    def test_build_system_prompt_basic(self):
        prompt = self.engine._build_system_prompt({})
        self.assertIn("JAMES", prompt)
        self.assertIn("INSTRUCTIONS", prompt)

    def test_build_system_prompt_with_context(self):
        ctx = {
            "target": "192.168.1.1",
            "interface": "wlan0",
            "discovered_services": {
                "192.168.1.1": {
                    "ports": ["22/tcp"],
                    "services": ["ssh"],
                }
            },
        }
        prompt = self.engine._build_system_prompt(ctx)
        self.assertIn("192.168.1.1", prompt)
        self.assertIn("DISCOVERED INFRASTRUCTURE", prompt)

    def test_urgency_signals_capture(self):
        ctx = {
            "capture_file": "/tmp/test.cap",
            "target_bssid": "AA:BB:CC",
        }
        signals = self.engine._build_urgency_signals(ctx)
        self.assertIn("URGENT", signals)

    def test_urgency_signals_attackable(self):
        ctx = {
            "discovered_services": {
                "10.0.0.1": {"services": ["ssh", "http"]}
            }
        }
        signals = self.engine._build_urgency_signals(ctx)
        self.assertIn("OPPORTUNITY", signals)

    def test_analyze_result_stores(self):
        """analyze_result always stores the result even without API."""
        self.engine.analyze_result(
            "scan", "22/tcp open ssh", {"target": "192.168.1.1"}
        )
        recent = self.engine.results.get_recent(1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["target"], "192.168.1.1")

    def test_process_returns_none_without_api(self):
        result = self.engine.process("scan 192.168.1.1", {})
        self.assertIsNone(result)

    def test_clear_all(self):
        self.engine.results.add("scan", "target", "result")
        self.engine.clear_all()
        self.assertEqual(len(self.engine.results.get_recent()), 0)


class TestNewPrimers(unittest.TestCase):
    """Test that new primers are registered and accessible."""

    def test_cracking_primer(self):
        from james.core.primers import get_primer, PRIMERS
        self.assertIn("cracking", PRIMERS)
        primer = get_primer("cracking")
        self.assertIn("PASSWORD CRACKING", primer)

    def test_post_exploit_primer(self):
        from james.core.primers import get_primer, PRIMERS
        self.assertIn("post-exploit", PRIMERS)
        primer = get_primer("post-exploit")
        self.assertIn("POST-EXPLOITATION", primer)

    def test_social_primer(self):
        from james.core.primers import get_primer, PRIMERS
        self.assertIn("social", PRIMERS)
        primer = get_primer("social")
        self.assertIn("SOCIAL ENGINEERING", primer)

    def test_primer_fallback(self):
        """Unknown phase returns system primer."""
        from james.core.primers import get_primer, SYSTEM_PRIMER
        primer = get_primer("nonexistent_phase")
        self.assertEqual(primer, SYSTEM_PRIMER)


if __name__ == "__main__":
    unittest.main()
