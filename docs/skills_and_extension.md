# 🛠️ Writing Custom Skills & Extension Guide — JAMES Linux

JAMES features a modular, template-driven architecture designed to make adding custom workflows (Skills) and wrapping new terminal tools simple and clean.

---

## 🛠️ The Skills System

A **Skill** in JAMES is an automated, multi-step pipeline represented as a JSON file stored in [james/skills/](file:///home/malcolm/Desktop/james-linux/james/skills).

### 1. JSON Skill Schema
Every skill file defines its name, metadata category, description, and list of sequential execution steps:

```json
{
  "name": "full_recon",
  "category": "network",
  "description": "Full network audit: scan, OS fingerprinting, and SMB checking",
  "version": "1.0",
  "author": "Operator",
  "steps": [
    {
      "action": "quick_recon",
      "description": "Quick Nmap port scan on {{target}}",
      "params": {
        "target": "{{target}}"
      }
    },
    {
      "action": "os_detect",
      "description": "Fingerprint OS for {{target}}",
      "params": {
        "target": "{{target}}"
      }
    },
    {
      "action": "smb_enum",
      "description": "Enumerate SMB shares on {{target}}",
      "params": {
        "target": "{{target}}"
      }
    }
  ]
}
```

### 2. Variable Template Resolution
The orchestrator parses skill parameters for template tags enclosed in double curly braces (e.g. `{{target}}`).
*   **Variable Substitution**: Before a step runs, the regex engine replaces matching keys with current session context variables (e.g., replacement logic parses `{{target}}` into `"192.168.1.5"` if `target` is set in the session context).
*   **Dynamic Dispatch**: The orchestrator matches the `action` string to an orchestrator class method using `getattr(self, action)` and executes it dynamically:
    `method = getattr(self, action)`
    `result = method(**params)`

---

## 🧩 Adding a New Tool Wrapper

To integrate a new command-line tool (e.g., `gobuster`) into JAMES:

### Step 1: Write the Tool Wrapper
Create or modify a wrapper class inside [james/tools/](file:///home/malcolm/Desktop/james-linux/james/tools) (typically `parrot.py`):

```python
class Gobuster:
    """Wrapper class for Gobuster directory brute-forcing."""

    def __init__(self, layer):
        self.layer = layer

    def dir_brute(self, url: str, wordlist: str, timeout: int = 120) -> dict:
        """Run gobuster dir command and parse results."""
        if not self.layer.check_tool("gobuster"):
            return {"error": "gobuster is not installed on the host"}

        import shlex
        cmd = f"gobuster dir -u {shlex.quote(url)} -w {shlex.quote(wordlist)} --quiet"
        
        # Run command using the NativeLayer
        result = self.layer.run(cmd, timeout=timeout)
        if not result.success:
            return {"success": False, "error": result.stderr or "Gobuster failed"}

        # Parse directory lines from stdout
        directories = []
        for line in result.stdout.splitlines():
            if "Status: 200" in line or "Status: 301" in line:
                directories.append(line.strip())

        return {
            "success": True,
            "directories_found": directories,
            "count": len(directories)
        }
```

### Step 2: Instantiate in the Orchestrator
Open [orchestrator.py](file:///home/malcolm/Desktop/james-linux/james/core/orchestrator.py), import the class, and instantiate it in the constructor:

```python
# Import wrapper
from james.tools.parrot import Gobuster

class Orchestrator:
    def __init__(self):
        self.layer = NativeLayer()
        # Instantiate
        self.gobuster = Gobuster(self.layer)
```

Expose a coordinating method in the orchestrator:

```python
    def web_dir_brute(self, url: str, wordlist: str = "") -> dict:
        """Run directory brute force on target URL."""
        # Auto-resolve wordlist from category if none provided
        wl = self.ensure_wordlist(wordlist or self.find_wordlist("web"))
        
        entry = self._log("web_dir_brute", "gobuster", {"url": url, "wordlist": wl})
        result = self.gobuster.dir_brute(url, wl)
        self._finish(entry, result)
        return result
```

### Step 3: Register Action in the Agent Brain
Open [ai_engine.py](file:///home/malcolm/Desktop/james-linux/james/core/ai_engine.py). Register the function and parameter mapping inside `TOOL_DECLARATIONS` so the Gemini model knows how to trigger it:

```python
    (
        "web_dir_brute",
        "Directory brute-forcing against web server",
        {
            "url": ("string", "Target URL to brute-force", True),
            "wordlist": ("string", "Custom wordlist path (optional)", False)
        },
        {"url": 1, "wordlist": 2}
    )
```

Also, add a matching Regex pattern to `INTENT_PATTERNS` inside [agent.py](file:///home/malcolm/Desktop/james-linux/james/core/agent.py) to support offline matching:

```python
    (r"(?:dir\s*brute|gobuster)\s+(\S+)(?:\s+(\S+))?", "web_dir_brute")
```

Once registered, the tool is accessible via regex chat commands, Gemini function calling, and custom JSON skills.
