import subprocess
import os

token = os.environ.get("GITHUB_TOKEN")
if token:
    print("Found GITHUB_TOKEN")
else:
    print("No GITHUB_TOKEN")
