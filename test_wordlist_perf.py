import unittest
import os
import tempfile
import time
from pathlib import Path
from james.core.orchestrator import Orchestrator

class TestWordlistPerf(unittest.TestCase):
    def setUp(self):
        self.orchestrator = Orchestrator()

    def test_cache_hit(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            for i in range(100):
                f.write(f"word{i}\n")
            temp_path = Path(f.name)

        try:
            # First call - cache miss
            start = time.time()
            lines1 = self.orchestrator._get_wordlist_lines(temp_path)
            t1 = time.time() - start

            # Second call - cache hit
            start = time.time()
            lines2 = self.orchestrator._get_wordlist_lines(temp_path)
            t2 = time.time() - start

            self.assertEqual(lines1, 100)
            self.assertEqual(lines2, 100)
            self.assertIn(str(temp_path), self.orchestrator._line_count_cache)
            self.assertTrue(t2 <= t1, f"Cache was not faster! t1={t1}, t2={t2}")

        finally:
            if temp_path.exists():
                temp_path.unlink()

if __name__ == '__main__':
    unittest.main()
