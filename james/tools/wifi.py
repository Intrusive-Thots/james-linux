"""Tool wrappers for wifi.

Extracted from parrot.py for modularity. Re-exported via james.tools.parrot.
"""
import json
import re
import shlex
import xml.etree.ElementTree as ET
from typing import Optional
from james.layers.native import NativeLayer, CommandResult

