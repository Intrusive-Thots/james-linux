#!/usr/bin/env python3
"""
Test suite for JAMES primers functionality.
"""
import sys

from james.core.primers import (
    get_combined_primer,
    SYSTEM_PRIMER,
    RECON_PRIMER,
    WIFI_PRIMER,
)

def test_get_combined_primer():
    """Test get_combined_primer output concatenation."""

    # 1. Empty phases
    result = get_combined_primer()
    assert result == SYSTEM_PRIMER, f"Expected SYSTEM_PRIMER, got {result!r}"

    # 2. Single valid phase
    result = get_combined_primer("recon")
    expected = "\n\n---\n\n".join([SYSTEM_PRIMER, RECON_PRIMER])
    assert result == expected, f"Expected {expected!r}, got {result!r}"

    # 3. Multiple valid phases
    result = get_combined_primer("recon", "wifi")
    expected = "\n\n---\n\n".join([SYSTEM_PRIMER, RECON_PRIMER, WIFI_PRIMER])
    assert result == expected, f"Expected {expected!r}, got {result!r}"

    # 4. Invalid phase
    result = get_combined_primer("nonexistent")
    assert result == SYSTEM_PRIMER, f"Expected SYSTEM_PRIMER, got {result!r}"

    # Mixed valid and invalid phase
    result = get_combined_primer("nonexistent", "wifi")
    expected = "\n\n---\n\n".join([SYSTEM_PRIMER, WIFI_PRIMER])
    assert result == expected, f"Expected {expected!r}, got {result!r}"

    # 5. Case insensitivity
    result = get_combined_primer("RECON", "WiFi")
    expected = "\n\n---\n\n".join([SYSTEM_PRIMER, RECON_PRIMER, WIFI_PRIMER])
    assert result == expected, f"Expected {expected!r}, got {result!r}"

    print("✅ All get_combined_primer tests passed.")

if __name__ == "__main__":
    try:
        test_get_combined_primer()
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
