import re

_CENSUS_SUFFIX = re.compile(
    r"\s+(?:city and borough|consolidated government \(balance\)"
    r"|metropolitan government \(balance\)|metro government \(balance\)"
    r"|unified government \(balance\)|charter township|city \(balance\)"
    r"|city|town|village|borough|township|municipality|plantation|CDP|CCD)$"
)
_DIRECTIONS = {"n": "north", "s": "south", "e": "east", "w": "west"}


def strip_census_suffix(name):
    """'Dallas city' -> 'Dallas', 'Edison township' -> 'Edison'."""
    return _CENSUS_SUFFIX.sub("", name.strip())


def city_key(name):
    """Turn a city name into a comparison key, so different spellings of the same place match."""
    key = name.lower().strip()
    key = re.sub(r"\s+(township|twp)$", "", key)
    first, _, rest = key.partition(" ")
    if rest and first in _DIRECTIONS:
        key = f"{_DIRECTIONS[first]} {rest}"
    key = re.sub(r"\bsainte\b", "ste", key)
    key = re.sub(r"\bsaint\b", "st", key)
    key = re.sub(r"\bmount\b", "mt", key)
    key = re.sub(r"\bfort\b", "ft", key)
    return re.sub(r"[^a-z0-9]", "", key)

def census_aliases(name):
    """Other names a Census place should also be found under."""
    aliases = set(re.split(r"[-/]", name))
    if name.endswith(" City"):
        aliases.add(name[: -len(" City")])
    aliases.discard(name)
    aliases.discard("")
    return aliases
