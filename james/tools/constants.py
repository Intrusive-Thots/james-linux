import re

# Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Regex Patterns
INTERFACE_REGEX = re.compile(r"^[a-zA-Z0-9._][a-zA-Z0-9._-]*$")
