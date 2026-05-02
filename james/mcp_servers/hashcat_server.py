from typing import Dict, Any
from .base_server import MCPToolClient
from james.layers.native import NativeLayer
import re

class HashcatServer(MCPToolClient):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(HashcatServer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, layer: NativeLayer = None):
        if not getattr(self, '_initialized', False):
            super().__init__("Hashcat MCP Server")
            self.layer = layer if layer else NativeLayer()
            self._initialized = True

            self.register_tool(
                "hashcat_run",
                "Run hashcat to crack a hash file using a wordlist. Arguments: hash_file (str), wordlist (str), mode (int). Mode 22000 is for WPA/WPA2, 2500 is for older WPA captures.",
                self.hashcat_run
            )

    def hashcat_run(self, hash_file: str, wordlist: str, mode: int) -> Dict[str, Any]:
        if mode not in [2500, 22000]:
            return {"status": "error", "message": f"Unsupported hash mode {mode}. Expected 22000 or 2500."}

        cmd = f"hashcat -m {mode} {hash_file} {wordlist} --show"
        result = self.layer.run(cmd, timeout=10) # check if already cracked

        if result.stdout and ":" in result.stdout:
            # Usually format is hash:password
            parts = result.stdout.strip().split(":")
            return {"status": "success", "password": parts[-1]}

        # Run actual cracking process
        cmd = f"hashcat -m {mode} {hash_file} {wordlist} -w 3 -O"
        # Since hashcat takes time, we run it and wait
        result = self.layer.run(cmd, timeout=300)

        if result.returncode == 0 or result.returncode == 1:
            cmd_show = f"hashcat -m {mode} {hash_file} {wordlist} --show"
            show_res = self.layer.run(cmd_show, timeout=10)
            if show_res.stdout and ":" in show_res.stdout:
                parts = show_res.stdout.strip().split(":")
                return {"status": "success", "password": parts[-1]}
            return {"status": "failed", "message": "Password not found in wordlist."}

        return {"status": "error", "message": result.stderr}
