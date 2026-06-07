"""
JAMES Wi-Fi Wordlist Generator.

Generates high-probability Wi-Fi password candidates based on known
patterns people actually use for their home and small-business routers.

WPA passwords: 8-63 characters.
Most common structures:
  - word + digits     (dragon123, password1)
  - Name + year       (Michael2024, Jessica99)
  - word + special    (letmein!, p@ssw0rd)
  - ISP defaults      (8-10 random digits/hex)
  - Keyboard walks    (qwerty123, 1q2w3e4r)
  - Phone numbers     (area code patterns)
  - All-digit PINs    (12345678, 00000000)
"""

import os
import itertools
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Base data ───────────────────────────────────────────────────

# Top Wi-Fi password roots (from real-world audits)
WIFI_ROOTS = [
    # Classic passwords
    "password",
    "12345678",
    "123456789",
    "1234567890",
    "qwerty123",
    "letmein",
    "welcome",
    "monkey",
    "dragon",
    "master",
    "shadow",
    "sunshine",
    "princess",
    "football",
    "baseball",
    "iloveyou",
    "trustno1",
    "batman",
    "access",
    "hello",
    "charlie",
    "donald",
    "loveme",
    "michael",
    "jordan",
    "mustang",
    "freedom",
    "whatever",
    "nothing",
    "internet",
    # Common English words used as WiFi passwords
    "password",
    "wireless",
    "internet",
    "network",
    "connect",
    "wifi",
    "home",
    "house",
    "family",
    "office",
    "guest",
    "admin",
    "default",
    "router",
    "linksys",
    "netgear",
    "comcast",
    "spectrum",
    "verizon",
    "xfinity",
    "att",
    "tmobile",
    "sprint",
    "frontier",
    "centurylink",
    # Location/object words
    "apartment",
    "building",
    "street",
    "house",
    "river",
    "mountain",
    "beach",
    "garden",
    "kitchen",
    "bedroom",
    "garage",
    "basement",
    "studio",
    "downtown",
    "uptown",
    # Animal names (very common wifi passwords)
    "butterfly",
    "dolphin",
    "elephant",
    "giraffe",
    "penguin",
    "goldfish",
    "hamster",
    "kitten",
    "puppy",
    "rabbit",
    "turtle",
    "chicken",
    "phoenix",
    "unicorn",
    "dragon",
    # Food/drink
    "chocolate",
    "coffee",
    "pizza",
    "burger",
    "cookies",
    "icecream",
    "pancake",
    "avocado",
    "banana",
    "strawberry",
    # Sports/hobbies
    "soccer",
    "tennis",
    "basketball",
    "baseball",
    "football",
    "swimming",
    "running",
    "fishing",
    "camping",
    "hiking",
    "gaming",
    "reading",
    "cooking",
    "dancing",
    "singing",
]

# Most common first names (US census)
COMMON_NAMES = [
    "james",
    "john",
    "robert",
    "michael",
    "david",
    "william",
    "richard",
    "joseph",
    "thomas",
    "charles",
    "christopher",
    "daniel",
    "matthew",
    "anthony",
    "mark",
    "donald",
    "steven",
    "paul",
    "andrew",
    "joshua",
    "kenneth",
    "kevin",
    "brian",
    "george",
    "timothy",
    "ronald",
    "edward",
    "jason",
    "jeffrey",
    "ryan",
    "jacob",
    "gary",
    "nicholas",
    "eric",
    "mary",
    "patricia",
    "jennifer",
    "linda",
    "barbara",
    "elizabeth",
    "susan",
    "jessica",
    "sarah",
    "karen",
    "lisa",
    "nancy",
    "betty",
    "margaret",
    "sandra",
    "ashley",
    "dorothy",
    "kimberly",
    "emily",
    "donna",
    "michelle",
    "carol",
    "amanda",
    "melissa",
    "deborah",
    "stephanie",
    "rebecca",
    "sharon",
    "laura",
    "cynthia",
    "kathleen",
    "amy",
    "angela",
    "shirley",
    "anna",
    "brenda",
    "pamela",
    "emma",
    "nicole",
    "helen",
    "samantha",
    "katherine",
    "christine",
    "debra",
]

# Common keyboard patterns
KEYBOARD_PATTERNS = [
    "qwerty",
    "qwertyuiop",
    "asdfghjkl",
    "zxcvbnm",
    "1q2w3e4r",
    "1q2w3e4r5t",
    "q1w2e3r4",
    "q1w2e3r4t5",
    "qwer1234",
    "asdf1234",
    "zxcv1234",
    "1qaz2wsx",
    "2wsx3edc",
    "qazwsxedc",
    "1qaz2wsx3edc",
    "asdfjkl;",
    "qweasdzxc",
    "poiuytrewq",
    "lkjhgfdsa",
    "mnbvcxz",
    "abcdefgh",
    "abcd1234",
]

# Common suffixes people add to make passwords "complex"
COMMON_SUFFIXES = [
    "",
    "1",
    "2",
    "3",
    "12",
    "13",
    "21",
    "23",
    "69",
    "77",
    "99",
    "01",
    "07",
    "11",
    "22",
    "33",
    "44",
    "55",
    "66",
    "88",
    "00",
    "10",
    "100",
    "111",
    "123",
    "321",
    "234",
    "345",
    "456",
    "567",
    "678",
    "789",
    "007",
    "420",
    "666",
    "777",
    "911",
    "1234",
    "2024",
    "2025",
    "2026",
    "!",
    "!!",
    "!!!",
    "@",
    "#",
    "$",
    "!1",
    "@1",
    "#1",
    "1!",
    "12!",
    "123!",
    "1234!",
]

# Year range for mutations
YEARS = list(range(1970, 2027))

# ISP default password patterns (commonly 8-10 chars)
ISP_PATTERNS = [
    # All numeric (8 digits) — very common for ISP routers
    "########",
    # Hex patterns (some ISPs use hex)
    "HHHHHHHH",  # 8 hex chars
    "HHHHHHHHHH",  # 10 hex chars
]


class WifiWordlistGenerator:
    """
    Generates high-probability Wi-Fi password candidates.

    Strategies:
      1. Common passwords (known Wi-Fi defaults + classics)
      2. Name-based (first names + year/digits)
      3. SSID-targeted (permutations of the network name)
      4. Keyboard patterns
      5. Numeric patterns (phone numbers, PINs)
      6. Mask-based patterns via hashcat masks
    """

    OUTPUT_DIR = Path.home() / ".james" / "wordlists"

    def __init__(self):
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def generate_wifi_common(self, output: Optional[str] = None) -> str:
        """
        Generate a curated Wi-Fi wordlist with high-probability candidates.
        Returns path to generated file.
        """
        output = output or str(self.OUTPUT_DIR / "wifi_common.txt")
        passwords = set()

        # 1. Raw roots (already valid as 8+ char passwords)
        for root in WIFI_ROOTS:
            if len(root) >= 8:
                passwords.add(root)
                passwords.add(root.capitalize())
                passwords.add(root.upper())

        # 2. Roots + common suffixes
        for root in WIFI_ROOTS:
            for suffix in COMMON_SUFFIXES:
                candidate = root + suffix
                if 8 <= len(candidate) <= 63:
                    passwords.add(candidate)
                    passwords.add(candidate.capitalize())

        # 3. Names + years
        for name in COMMON_NAMES:
            for year in YEARS:
                candidate = name + str(year)
                if len(candidate) >= 8:
                    passwords.add(candidate)
                    passwords.add(candidate.capitalize())
                    passwords.add(name.capitalize() + str(year))

            # Names + 2-3 digit suffixes
            for suffix in ["123", "1234", "!", "!!", "01", "69", "99", "007"]:
                candidate = name + suffix
                if 8 <= len(candidate) <= 63:
                    passwords.add(candidate)
                    passwords.add(candidate.capitalize())

        # 4. Keyboard patterns
        for pattern in KEYBOARD_PATTERNS:
            if len(pattern) >= 8:
                passwords.add(pattern)
            for suffix in ["123", "1234", "!", "!!", "1", "12"]:
                candidate = pattern + suffix
                if 8 <= len(candidate) <= 63:
                    passwords.add(candidate)

        # 5. Numeric patterns
        # Common 8-digit PINs
        for prefix in ["12345", "11111", "00000", "99999", "55555"]:
            for suffix in ["678", "111", "000", "999", "123", "234", "321"]:
                candidate = prefix + suffix
                if len(candidate) == 8:
                    passwords.add(candidate)

        # Repeated digits
        for d in "0123456789":
            passwords.add(d * 8)
            passwords.add(d * 9)
            passwords.add(d * 10)

        # Sequential
        passwords.add("12345678")
        passwords.add("123456789")
        passwords.add("1234567890")
        passwords.add("0123456789")
        passwords.add("87654321")
        passwords.add("9876543210")

        # Common phone-like patterns (8 digits)
        for area in ["212", "310", "415", "305", "713", "202", "312", "404"]:
            for last4 in ["0000", "1234", "5678", "1111", "9999"]:
                passwords.add(area + "555" + last4[-1])  # Placeholder

        # 6. Common ISP defaults
        passwords.add("admin1234")
        passwords.add("password1")
        passwords.add("changeme1")
        passwords.add("default1")

        # Filter: WPA requires 8-63 chars
        valid = sorted(p for p in passwords if 8 <= len(p) <= 63)

        with open(output, "w") as f:
            f.write("\n".join(valid) + "\n")

        logger.info(
            "Generated Wi-Fi wordlist: %s (%d candidates)", output, len(valid)
        )
        return output

    def generate_ssid_targeted(
        self, ssid: str, output: Optional[str] = None
    ) -> str:
        """
        Generate a targeted wordlist based on the SSID name.
        People often use their network name in their password.
        """
        output = output or str(
            self.OUTPUT_DIR / f"ssid_{ssid.replace(' ', '_')}.txt"
        )
        passwords = set()

        # Clean SSID
        ssid_clean = ssid.strip()
        ssid_lower = ssid_clean.lower()
        ssid_upper = ssid_clean.upper()
        ssid_cap = ssid_clean.capitalize()
        # Remove common ISP suffixes
        ssid_base = (
            ssid_lower.replace("-5g", "")
            .replace("-2g", "")
            .replace("_5ghz", "")
            .replace("_2.4ghz", "")
            .replace("-guest", "")
            .replace("_guest", "")
        )

        variants = {
            ssid_clean,
            ssid_lower,
            ssid_upper,
            ssid_cap,
            ssid_base,
            ssid_base.capitalize(),
        }

        for v in list(variants):
            # SSID + digits
            for suffix in COMMON_SUFFIXES:
                candidate = v + suffix
                if 8 <= len(candidate) <= 63:
                    passwords.add(candidate)

            # SSID + year
            for year in range(2015, 2027):
                candidate = v + str(year)
                if 8 <= len(candidate) <= 63:
                    passwords.add(candidate)

            # SSID reversed
            rev = v[::-1]
            if 8 <= len(rev) <= 63:
                passwords.add(rev)

            # Leet speak
            leet = (
                v.replace("a", "@")
                .replace("e", "3")
                .replace("i", "1")
                .replace("o", "0")
                .replace("s", "$")
            )
            if 8 <= len(leet) <= 63:
                passwords.add(leet)
                for suffix in ["123", "!", "1", "12"]:
                    passwords.add(leet + suffix)

            # With separators
            for sep in ["_", "-", ".", "@", "#"]:
                for suffix in ["wifi", "net", "home", "123", "pass", "key"]:
                    candidate = v + sep + suffix
                    if 8 <= len(candidate) <= 63:
                        passwords.add(candidate)

        # Extract words from SSID (e.g., "SmithFamily" -> smith, family)
        import re

        words = re.findall(r"[A-Z][a-z]+|[a-z]+|[A-Z]+|\d+", ssid_clean)
        for word in words:
            word_l = word.lower()
            if len(word_l) >= 3:
                for suffix in COMMON_SUFFIXES:
                    candidate = word_l + suffix
                    if 8 <= len(candidate) <= 63:
                        passwords.add(candidate)
                        passwords.add(candidate.capitalize())

        # Combinations of SSID words
        if len(words) >= 2:
            for perm in itertools.permutations(words, 2):
                candidate = "".join(perm).lower()
                if 8 <= len(candidate) <= 63:
                    passwords.add(candidate)
                    passwords.add(candidate.capitalize())
                for suffix in ["123", "!", "1", "2024", "2025"]:
                    c2 = candidate + suffix
                    if 8 <= len(c2) <= 63:
                        passwords.add(c2)

        valid = sorted(p for p in passwords if 8 <= len(p) <= 63)

        with open(output, "w") as f:
            f.write("\n".join(valid) + "\n")

        logger.info(
            "Generated SSID-targeted wordlist for '%s': %s (%d candidates)",
            ssid,
            output,
            len(valid),
        )
        return output

    def generate_numeric(self, output: Optional[str] = None) -> str:
        """
        Generate all-numeric password candidates.
        Covers: 8-digit PINs, phone patterns, ISP defaults.
        """
        output = output or str(self.OUTPUT_DIR / "wifi_numeric.txt")
        passwords = set()

        # All 8-digit repeating patterns (00000000 through 99999999 repeating)
        for d in "0123456789":
            passwords.add(d * 8)
            passwords.add(d * 10)

        # Sequential
        for start in range(0, 10):
            seq = "".join(str((start + i) % 10) for i in range(8))
            passwords.add(seq)
            seq10 = "".join(str((start + i) % 10) for i in range(10))
            passwords.add(seq10)

        # Common numeric passwords
        for p in [
            "12345678",
            "123456789",
            "1234567890",
            "87654321",
            "11111111",
            "22222222",
            "00000000",
            "99999999",
            "12341234",
            "12121212",
            "13131313",
            "10101010",
            "11223344",
            "55555555",
            "77777777",
            "88888888",
            "19901990",
            "20002000",
            "20202020",
            "20242024",
            "19801980",
            "19851985",
            "19951995",
            "20102010",
            "31415926",  # pi
            "27182818",  # e
            "01234567",
            "76543210",
            "98765432",
            "13579246",
            "24681357",
            "11235813",  # fibonacci
        ]:
            passwords.add(p)

        # Date patterns (MMDDYYYY, DDMMYYYY)
        for month in range(1, 13):
            for day in [1, 10, 15, 20, 25]:
                for year in range(1960, 2027):
                    mmdd = f"{month:02d}{day:02d}{year}"
                    ddmm = f"{day:02d}{month:02d}{year}"
                    passwords.add(mmdd)
                    passwords.add(ddmm)
                    # YYYYMMDD
                    passwords.add(f"{year}{month:02d}{day:02d}")

        # Phone-number style (common US area codes + 7 digits)
        for area in [
            "212",
            "310",
            "415",
            "305",
            "713",
            "202",
            "312",
            "404",
            "617",
            "206",
            "503",
            "512",
            "702",
            "818",
        ]:
            for mid in ["555", "123", "000", "999"]:
                for last in range(0, 10000, 1111):
                    p = f"{area}{mid}{last:04d}"
                    passwords.add(p)

        valid = sorted(p for p in passwords if 8 <= len(p) <= 63)

        with open(output, "w") as f:
            f.write("\n".join(valid) + "\n")

        logger.info(
            "Generated numeric wordlist: %s (%d candidates)",
            output,
            len(valid),
        )
        return output

    def get_combined_wordlist(
        self, ssid: str = "", output: Optional[str] = None
    ) -> str:
        """
        Generate a combined 'ultimate' Wi-Fi wordlist merging all strategies.
        Returns path to the combined file.
        """
        output = output or str(self.OUTPUT_DIR / "wifi_ultimate.txt")
        all_passwords = set()

        # Load from each generator
        common = self.generate_wifi_common()
        numeric = self.generate_numeric()

        for path in [common, numeric]:
            with open(path) as f:
                all_passwords.update(map(str.strip, f))

        all_passwords.discard("")

        # SSID-targeted if SSID given
        if ssid:
            ssid_file = self.generate_ssid_targeted(ssid)
            with open(ssid_file) as f:
                all_passwords.update(map(str.strip, f))

        all_passwords.discard("")

        # Also pull from system wordlists if they exist
        for sys_file in [
            "/usr/share/wordlists/probable-v2-wpa-top4800.txt",
            "/usr/share/fern-wifi-cracker/extras/wordlists/common.txt",
        ]:
            if os.path.exists(sys_file):
                try:
                    with open(sys_file, "r", errors="ignore") as f:
                        all_passwords.update([l for l in map(str.strip, f) if 8 <= len(l) <= 63])
                except Exception:
                    pass

        valid = sorted(all_passwords)

        with open(output, "w") as f:
            f.write("\n".join(valid) + "\n")

        logger.info(
            "Generated ultimate Wi-Fi wordlist: %s (%d candidates)",
            output,
            len(valid),
        )
        return output
