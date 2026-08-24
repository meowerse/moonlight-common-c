#!/usr/bin/env python3
"""Verify the ControlStream.c packet type tables stay aligned.

src/ControlStream.c indexes five parallel `packetTypesGen*` arrays with the same
set of IDX_* constants. If one array is shorter than the others, a lookup for a
high index silently reads the wrong packet type or past the end of the array.
This has already happened once in this file's history, so it is checked in CI
rather than by eye.

Asserts:
  1. All five packetTypesGen* arrays exist and have identical length.
  2. Every IDX_* constant is in bounds for that length.

Exits non-zero on failure.
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(REPO_ROOT, "src", "ControlStream.c")

EXPECTED_ARRAYS = [
    "packetTypesGen3",
    "packetTypesGen4",
    "packetTypesGen5",
    "packetTypesGen7",
    "packetTypesGen7Enc",
]

ARRAY_RE = re.compile(
    r"static\s+const\s+short\s+(packetTypesGen\w*)\s*\[\s*\]\s*=\s*\{(.*?)\};",
    re.DOTALL,
)
IDX_RE = re.compile(r"^#define\s+(IDX_\w+)\s+(\d+)\s*$", re.MULTILINE)


def count_entries(body):
    # Strip // comments, then count comma-separated non-empty entries.
    body = re.sub(r"//[^\n]*", "", body)
    return len([e for e in body.split(",") if e.strip()])


def main():
    source = open(SOURCE, encoding="utf-8").read()

    arrays = {name: count_entries(body) for name, body in ARRAY_RE.findall(source)}
    indices = {name: int(value) for name, value in IDX_RE.findall(source)}

    failures = []

    print("packet type arrays in %s:" % os.path.relpath(SOURCE, REPO_ROOT))
    for name in EXPECTED_ARRAYS:
        if name not in arrays:
            failures.append("array %s not found" % name)
            print("  %-20s MISSING" % name)
        else:
            print("  %-20s %d entries" % (name, arrays[name]))

    for name in sorted(set(arrays) - set(EXPECTED_ARRAYS)):
        failures.append("unexpected extra array %s (update EXPECTED_ARRAYS)" % name)
        print("  %-20s %d entries  UNEXPECTED" % (name, arrays[name]))

    lengths = set(arrays.values())
    if len(lengths) > 1:
        failures.append("arrays have differing lengths: %s" % sorted(lengths))
    print("\nall arrays same length: %s" % ("YES" if len(lengths) == 1 else "NO"))

    if not indices:
        failures.append("no IDX_* constants found")

    bound = min(lengths) if lengths else 0
    print("\nIDX_* constants (bound = %d):" % bound)
    for name, value in sorted(indices.items(), key=lambda kv: (kv[1], kv[0])):
        ok = 0 <= value < bound
        if not ok:
            failures.append("%s = %d is out of bounds (0..%d)" % (name, value, bound - 1))
        print("  %-36s %2d  %s" % (name, value, "ok" if ok else "OUT OF BOUNDS"))

    print("")
    if failures:
        for f in failures:
            print("FAIL: %s" % f)
        return 1

    print("PASS: %d arrays x %d entries, %d IDX_* constants all in bounds"
          % (len(arrays), bound, len(indices)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
