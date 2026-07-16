import pytest
import string
from james.remote.gui_remote import GUIRemote

def test_generate_vnc_password():
    # Since _generate_vnc_password does not use 'self', we can call it on an instance
    # if it doesn't require init args, or mock it.
    # Looking at the code in james/remote/gui_remote.py, __init__ does NOT take any arguments!
    # Let's verify by just instantiating it.

    gui_remote = GUIRemote()

    # Test length
    password = gui_remote._generate_vnc_password()
    assert len(password) == 8

    # Test character sets
    # The actual implementation in james/remote/gui_remote.py uses:
    # secrets.token_urlsafe(6)[:8]
    # which is 8 characters from the URL-safe base64 alphabet (A-Za-z0-9-_).
    for char in password:
        assert char in string.ascii_letters + string.digits + "-_"

    # Test randomness (generate multiple and ensure they're different)
    passwords = set(gui_remote._generate_vnc_password() for _ in range(100))
    assert len(passwords) > 1
