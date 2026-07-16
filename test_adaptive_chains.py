"""
Tests for adaptive chain infrastructure and ResultStore integration.

Tests the new _extract_open_services, _store_chain_result, and
cross-chain intelligence wiring.
"""

import pytest
import sys
import os
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock
from collections import deque

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from james.core.ai_engine import ResultStore


def _make_result_store():
    """Create a ResultStore that doesn't touch disk."""
    store = ResultStore.__new__(ResultStore)
    store._store = deque(maxlen=ResultStore.MAX_RESULTS)
    return store


def _make_extract_services_fn():
    """
    Get a standalone reference to _extract_open_services that doesn't
    require a full Orchestrator instance.
    """
    from james.core.orchestrator import Orchestrator
    # Create a minimal object with just the method bound
    obj = object.__new__(Orchestrator)
    return obj._extract_open_services


class TestExtractOpenServices:
    """Test the _extract_open_services helper in Orchestrator."""

    def setup_method(self):
        self.fn = _make_extract_services_fn()

    def test_empty_scan(self):
        result = self.fn({"hosts": []})
        assert result["ports"] == []
        assert result["has_web"] is False
        assert result["has_smb"] is False
        assert result["has_ssh"] is False
        assert result["has_ftp"] is False
        assert result["has_db"] is False

    def test_ssh_only(self):
        scan = {"hosts": [{
            "address": "10.0.0.1",
            "state": "up",
            "ports": [
                {"port": 22, "protocol": "tcp", "state": "open",
                 "service": "ssh", "version": "OpenSSH 8.9"},
            ],
        }]}
        result = self.fn(scan)
        assert result["has_ssh"] is True
        assert result["has_web"] is False
        assert result["has_smb"] is False
        assert 22 in result["ports"]

    def test_web_and_smb(self):
        scan = {"hosts": [{
            "address": "10.0.0.1",
            "state": "up",
            "ports": [
                {"port": 80, "protocol": "tcp", "state": "open",
                 "service": "http", "version": "nginx 1.18"},
                {"port": 443, "protocol": "tcp", "state": "open",
                 "service": "https", "version": ""},
                {"port": 445, "protocol": "tcp", "state": "open",
                 "service": "microsoft-ds", "version": ""},
            ],
        }]}
        result = self.fn(scan)
        assert result["has_web"] is True
        assert result["has_smb"] is True
        assert result["has_ssh"] is False
        assert set(result["ports"]) == {80, 443, 445}

    def test_database_detection(self):
        scan = {"hosts": [{
            "address": "10.0.0.1",
            "state": "up",
            "ports": [
                {"port": 3306, "protocol": "tcp", "state": "open",
                 "service": "mysql", "version": "MySQL 8.0"},
            ],
        }]}
        result = self.fn(scan)
        assert result["has_db"] is True
        assert "mysql" in result["services"]

    def test_ftp_detection(self):
        scan = {"hosts": [{
            "address": "10.0.0.1",
            "state": "up",
            "ports": [
                {"port": 21, "protocol": "tcp", "state": "open",
                 "service": "ftp", "version": "vsftpd 3.0"},
            ],
        }]}
        result = self.fn(scan)
        assert result["has_ftp"] is True
        assert result["has_ssh"] is False

    def test_port_only_detection_no_service_name(self):
        """Test that detection works via port number alone even without service name."""
        scan = {"hosts": [{
            "address": "10.0.0.1",
            "state": "up",
            "ports": [
                {"port": 22, "protocol": "tcp", "state": "open",
                 "service": "", "version": ""},
                {"port": 80, "protocol": "tcp", "state": "open",
                 "service": "", "version": ""},
            ],
        }]}
        result = self.fn(scan)
        # Even without service names, port-based detection should work
        assert result["has_ssh"] is True
        assert result["has_web"] is True

    def test_all_services_tuple(self):
        scan = {"hosts": [{
            "address": "10.0.0.1",
            "state": "up",
            "ports": [
                {"port": 22, "protocol": "tcp", "state": "open",
                 "service": "ssh", "version": "OpenSSH"},
                {"port": 80, "protocol": "tcp", "state": "open",
                 "service": "http", "version": "nginx"},
            ],
        }]}
        result = self.fn(scan)
        assert len(result["all_services"]) == 2
        assert result["all_services"][0] == (22, "tcp", "ssh", "OpenSSH")
        assert result["all_services"][1] == (80, "tcp", "http", "nginx")

    def test_multiple_hosts(self):
        scan = {"hosts": [
            {
                "address": "10.0.0.1",
                "state": "up",
                "ports": [
                    {"port": 22, "protocol": "tcp", "state": "open",
                     "service": "ssh", "version": ""},
                ],
            },
            {
                "address": "10.0.0.2",
                "state": "up",
                "ports": [
                    {"port": 445, "protocol": "tcp", "state": "open",
                     "service": "microsoft-ds", "version": ""},
                ],
            },
        ]}
        result = self.fn(scan)
        assert result["has_ssh"] is True
        assert result["has_smb"] is True
        assert 22 in result["ports"]
        assert 445 in result["ports"]

    def test_redis_is_db(self):
        scan = {"hosts": [{
            "address": "10.0.0.1", "state": "up",
            "ports": [
                {"port": 6379, "protocol": "tcp", "state": "open",
                 "service": "redis", "version": ""},
            ],
        }]}
        result = self.fn(scan)
        assert result["has_db"] is True

    def test_http_proxy_is_web(self):
        scan = {"hosts": [{
            "address": "10.0.0.1", "state": "up",
            "ports": [
                {"port": 8080, "protocol": "tcp", "state": "open",
                 "service": "http-proxy", "version": ""},
            ],
        }]}
        result = self.fn(scan)
        assert result["has_web"] is True


class TestStoreChainResult:
    """Test the _store_chain_result helper stores data in ResultStore."""

    def _make_orch_stub(self, store):
        """Create a minimal object with _store_chain_result bound."""
        from james.core.orchestrator import Orchestrator

        class Stub:
            _result_store = store
        obj = Stub()
        obj._store_chain_result = Orchestrator._store_chain_result.__get__(
            obj, Stub
        )
        return obj

    def test_stores_in_result_store(self):
        store = _make_result_store()
        orch = self._make_orch_stub(store)

        orch._store_chain_result(
            "network_dominate", "full_scan", "10.0.0.1",
            {"hosts": [{"address": "10.0.0.1", "ports": [{"port": 22}]}]}
        )

        results = store.get_recent(1)
        assert len(results) == 1
        assert "network_dominate" in results[0]["action"]
        assert results[0]["target"] == "10.0.0.1"
        assert "1 host(s)" in results[0]["summary"]

    def test_stores_error_result(self):
        store = _make_result_store()
        orch = self._make_orch_stub(store)

        orch._store_chain_result(
            "web_pwn", "waf_detect", "example.com",
            {"error": "connection refused"}
        )

        results = store.get_recent(1)
        assert len(results) == 1
        assert "ERROR" in results[0]["summary"]

    def test_no_store_does_not_crash(self):
        """Ensure _store_chain_result is a no-op when no result store is set."""
        from james.core.orchestrator import Orchestrator

        class Stub:
            _result_store = None
        obj = Stub()
        obj._store_chain_result = Orchestrator._store_chain_result.__get__(
            obj, Stub
        )
        # Should not raise
        obj._store_chain_result("test", "step", "target", {"data": "value"})

    def test_stores_findings_count(self):
        store = _make_result_store()
        orch = self._make_orch_stub(store)

        orch._store_chain_result(
            "web_pwn", "dir_bust", "http://example.com",
            {"findings": [{"path": "/admin"}, {"path": "/login"}]}
        )

        results = store.get_recent(1)
        assert "2 finding(s)" in results[0]["summary"]

    def test_stores_vuln_count(self):
        store = _make_result_store()
        orch = self._make_orch_stub(store)

        orch._store_chain_result(
            "web_pwn", "nikto", "http://example.com",
            {"vulnerabilities": ["xss", "csrf", "sqli"]}
        )

        results = store.get_recent(1)
        assert "3 vuln(s)" in results[0]["summary"]

    def test_stores_count_field(self):
        store = _make_result_store()
        orch = self._make_orch_stub(store)

        orch._store_chain_result(
            "stealth_recon", "dns", "example.com",
            {"count": 5}
        )

        results = store.get_recent(1)
        assert "5 result(s)" in results[0]["summary"]


class TestCrossChainIntelligence:
    """Test that ResultStore enables cross-chain intelligence."""

    def test_search_finds_prior_scans(self):
        store = _make_result_store()

        # Simulate stealth_recon storing results
        store.add("stealth_recon/osint", "10.0.0.1",
                   "Found 3 hosts, 12 ports")

        # A subsequent network_dominate handler should find this
        prior = store.search("10.0.0.1", n=3)
        assert len(prior) >= 1
        assert "10.0.0.1" in prior[0]["target"]

    def test_search_across_chains(self):
        """Test that results from one chain are findable from another."""
        store = _make_result_store()
        store.add("stealth_recon/osint", "example.com",
                   "Found 3 subdomains: api.example.com, mail.example.com")
        store.add("stealth_recon/dns", "example.com",
                   "Resolved 2 IPs: 1.2.3.4, 5.6.7.8")

        results = store.search("example.com", n=5)
        assert len(results) == 2
        assert any("osint" in r["action"] for r in results)
        assert any("dns" in r["action"] for r in results)

    def test_chain_results_ordered_recent_first(self):
        """Results should come back newest-first."""
        store = _make_result_store()
        store.add("chain1/step1", "target", "first")
        store.add("chain1/step2", "target", "second")
        store.add("chain2/step1", "target", "third")

        results = store.search("target", n=3)
        assert results[0]["summary"] == "third"
        assert results[1]["summary"] == "second"
        assert results[2]["summary"] == "first"

    def test_search_by_action(self):
        """Can search by chain/step name too."""
        store = _make_result_store()
        store.add("network_dominate/full_scan", "10.0.0.1", "ports found")
        store.add("web_pwn/nikto", "example.com", "vulns found")

        results = store.search("network_dominate", n=5)
        assert len(results) == 1
        assert "full_scan" in results[0]["action"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
