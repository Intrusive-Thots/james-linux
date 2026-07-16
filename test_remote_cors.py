import unittest
import threading
import requests
import time
import os
from james.remote.server import RemoteServer

class DummyAgent:
    def __init__(self):
        self.context = {}

    def process(self, cmd):
        return "Dummy"

class TestCORS(unittest.TestCase):
    def setUp(self):
        os.environ["JAMES_CORS_ORIGINS"] = "http://allowed.com"
        self.server = RemoteServer(DummyAgent(), port=1345)
        self.server.start()
        time.sleep(0.5)
        self.url = f"http://127.0.0.1:1345/api/status"

    def tearDown(self):
        self.server.stop()
        if "JAMES_CORS_ORIGINS" in os.environ:
            del os.environ["JAMES_CORS_ORIGINS"]
        time.sleep(0.5)

    def test_options_allowed_origin(self):
        headers = {"Origin": "http://allowed.com"}
        res = requests.options(self.url, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "http://allowed.com")

    def test_options_not_allowed_origin(self):
        headers = {"Origin": "http://evil.com"}
        res = requests.options(self.url, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.headers.get("Access-Control-Allow-Origin"))

if __name__ == "__main__":
    unittest.main()
