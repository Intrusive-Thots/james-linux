import unittest
import os
import importlib
from fastapi.testclient import TestClient

class TestCORS(unittest.TestCase):
    def test_cors_default_rejects_evil(self):
        if "JAMES_CORS_ORIGINS" in os.environ:
            del os.environ["JAMES_CORS_ORIGINS"]

        import james.api.server
        importlib.reload(james.api.server)
        client = TestClient(james.api.server.app)

        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        self.assertNotEqual(
            response.headers.get("access-control-allow-origin"),
            "http://evil.com"
        )
        self.assertEqual(response.status_code, 400)

    def test_cors_default_allows_localhost(self):
        if "JAMES_CORS_ORIGINS" in os.environ:
            del os.environ["JAMES_CORS_ORIGINS"]

        import james.api.server
        importlib.reload(james.api.server)
        client = TestClient(james.api.server.app)

        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3000"
        )
        self.assertEqual(response.status_code, 200)

    def test_cors_custom_env(self):
        os.environ["JAMES_CORS_ORIGINS"] = "http://custom.com, https://other.org"

        import james.api.server
        importlib.reload(james.api.server)
        client = TestClient(james.api.server.app)

        response1 = client.options(
            "/api/health",
            headers={
                "Origin": "http://custom.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        self.assertEqual(
            response1.headers.get("access-control-allow-origin"),
            "http://custom.com"
        )
        self.assertEqual(response1.status_code, 200)

        response2 = client.options(
            "/api/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        self.assertNotEqual(
            response2.headers.get("access-control-allow-origin"),
            "http://evil.com"
        )
        self.assertEqual(response2.status_code, 400)

        del os.environ["JAMES_CORS_ORIGINS"]

if __name__ == '__main__':
    unittest.main()
